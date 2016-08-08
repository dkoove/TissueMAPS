import os.path as p
import json
import logging
import numpy as np
from cStringIO import StringIO
from zipfile import ZipFile

from geoalchemy2.shape import to_shape
import skimage.draw

from flask.ext.jwt import jwt_required
from flask.ext.jwt import current_identity
from flask.ext.jwt import jwt_required
from flask import jsonify, request, send_file
from sqlalchemy.sql import text
from werkzeug import secure_filename

import tmlib.models as tm
from tmlib.image import SegmentationImage

from tmserver.api import api
from tmserver.extensions import db
from tmserver.util import extract_model_from_path, assert_request_params
from tmserver.error import MalformedRequestError, ResourceNotFoundError


logger = logging.getLogger(__name__)


@api.route(
    '/experiments/<experiment_id>/mapobjects/<object_name>/tile',
    methods=['GET']
)
@assert_request_params('x', 'y', 'z', 'zplane', 'tpoint')
@extract_model_from_path(tm.Experiment)
def get_mapobjects_tile(experiment, object_name):

    # The coordinates of the requested tile
    x = request.args.get('x', type=int)
    y = request.args.get('y', type=int)
    # "z" is the pyramid zoom level and "zlevel" the z-resolution of the
    # acquired image
    z = request.args.get('z', type=int)
    zplane = request.args.get('zplane', type=int)
    tpoint = request.args.get('tpoint', type=int)

    logger.debug(
        'get mapobject tile: x=%d, y=%d, z=%d, zplane=%d, tpoint=%d',
        x, y, z, zplane, tpoint
    )

    if object_name == 'DEBUG_TILE':
        maxzoom = experiment.channels[0].layers[0].maxzoom_level_index
        minx, miny, maxx, maxy = tm.MapobjectSegmentation.bounding_box(
            x, y, z, maxzoom
        )
        return jsonify({
            'type': 'Feature',
            'geometry': {
                'type': 'Polygon',
                'coordinates': [[
                    [maxx, maxy], [minx, maxy], [minx, miny], [maxx, miny],
                    [maxx, maxy]
                ]]
            },
            'properties': {
                'x': x,
                'y': y,
                'z': z,
                'type': 'DEBUG_TILE'
            }
        })

    mapobject_type = db.session.query(tm.MapobjectType).\
        filter_by(name=object_name, experiment_id=experiment.id).\
        one()
    query_res = mapobject_type.get_mapobject_outlines_within_tile(
        x, y, z, tpoint, zplane
    )

    features = []
    if len(query_res) > 0:
        # Try to estimate how many points there are in total within
        # the polygons of this tile.
        # TODO: Make this more light weight by sending binary coordinates
        # without GEOJSON overhead. Requires a hack on the client side.
        for mapobject_id, geom_geojson_str in query_res:
            feature = {
                "type": "Feature",
                "id": mapobject_id,
                "geometry": json.loads(geom_geojson_str),
                "properties": {
                    "type": object_name
                }
            }
            features.append(feature)

    return jsonify({
        "type": "FeatureCollection",
        "features": features
    })


@api.route('/experiments/<experiment_id>/features', methods=['GET'])
@jwt_required()
@extract_model_from_path(tm.Experiment, check_ownership=True)
def get_features(experiment):
    """Sends a list of feature objects.

    Request
    -------

    Required GET parameters:
        - experiment_id

    Response
    --------

    {
        "data": {
            mapobject_type_name: [
                {
                    "name": string
                },
                ...
            ],
            ...
        }
    }

    """
    features = db.session.query(tm.Feature).\
        filter_by(experiment_id=experiment.id).\
        all()
    if not features:
        logger.waring('no features found')
    return jsonify({
        'data': features
    })


@api.route(
    '/experiments/<experiment_id>/mapobjects/<object_name>/segmentations',
    methods=['GET']
)
@jwt_required()
@assert_request_params('plate_name', 'well_name', 'x', 'y', 'zplane', 'tpoint')
@extract_model_from_path(tm.Experiment)
def get_mapobjects_segmentation(experiment, object_name):
    plate_name = request.args.get('plate_name')
    well_name = request.args.get('well_name')
    # TODO: raise MissingGETParameterError when arg missing
    x = request.args.get('x', type=int)
    y = request.args.get('y', type=int)
    zplane = request.args.get('zplane', type=int)
    tpoint = request.args.get('tpoint', type=int)
    label = request.args.get('label', None)
    site = db.session.query(tm.Site).\
        join(tm.Well).\
        join(tm.Plate).\
        filter(
            tm.Plate.experiment_id == experiment.id,
            tm.Plate.name == plate_name,
            tm.Well.name == well_name,
            tm.Site.x == x, tm.Site.y == y
        ).\
        one()
    mapobject_type = db.session.query(tm.MapobjectType).\
        filter_by(name=object_name, experiment_id=experiment.id).\
        one()
    segmentations = db.session.query(
            tm.MapobjectSegmentation.label,
            tm.MapobjectSegmentation.geom_poly
        ).\
        join(tm.Mapobject).\
        join(tm.MapobjectType).\
        filter(
            tm.MapobjectType.name == object_name,
            tm.MapobjectType.experiment_id == experiment.id,
            tm.MapobjectSegmentation.site_id == site.id,
            tm.MapobjectSegmentation.zplane == zplane,
            tm.MapobjectSegmentation.tpoint == tpoint
        ).\
        all()

    if len(segmentations) == 0:
        raise ResourceNotFoundError('No segmentations found.')
    polygons = dict()
    for seg in segmentations:
        polygons[(tpoint, zplane, seg.label)] = seg.geom_poly

    height = site.height - (
        site.intersection.lower_overhang + site.intersection.upper_overhang
    )
    width = site.width - (
        site.intersection.left_overhang + site.intersection.right_overhang
    )
    y_offset, x_offset = site.offset
    y_offset += site.intersection.lower_overhang
    x_offset += site.intersection.right_overhang

    img = SegmentationImage.create_from_polygons(
        polygons, y_offset, x_offset, (height, width)
    )
    f = StringIO()
    f.write(img.encode('png'))
    f.seek(0)
    filename = '%s_%s_x%.3d_y%.3d_z%.3d_t%.3d_%s.png' % (
        experiment.name, site.well.name, site.x, site.y, zplane, tpoint,
        object_name
    )
    return send_file(
        f,
        attachment_filename=secure_filename(filename),
        mimetype='image/png',
        as_attachment=True
    )


@api.route(
    '/experiments/<experiment_id>/mapobjects/<object_name>/feature-values',
    methods=['GET']
)
@jwt_required()
@extract_model_from_path(tm.Experiment)
def get_feature_values(experiment, object_name):
    mapobject_type = db.session.query(tm.MapobjectType).\
        filter_by(experiment_id=experiment.id, name=object_name).\
        one()
    features = mapobject_type.get_feature_value_matrix()
    metadata = mapobject_type.get_metadata_matrix()
    if features.values.shape[0] != metadata.values.shape[0]:
        raise ValueError(
            'Features and metadata must have same number of "%s" objects'
            % object_name
        )
    if any(features.index.values != metadata.index.values):
        raise ValueError(
            'Features and metadata must have the same index.'
        )
    basename = secure_filename(
        '%s_%s_features' % (experiment.name, object_name)
    )
    data_filename = '%s_data.csv' % basename
    metadata_filename = '%s_metadata.csv' % basename
    f = StringIO()
    with ZipFile(f, 'w') as zf:
        zf.writestr(
            data_filename,
            features.to_csv(None, encoding='utf-8', index=False)
        )
        zf.writestr(
            metadata_filename,
            metadata.to_csv(None, encoding='utf-8', index=False)
        )
    f.seek(0)
    return send_file(
        f,
        attachment_filename='%s.zip' % basename,
        mimetype='application/octet-stream',
        as_attachment=True
    )
