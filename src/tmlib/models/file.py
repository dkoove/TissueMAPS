import os
import logging
import numpy as np
from sqlalchemy import Column, String, Integer, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy import UniqueConstraint

from tmlib.utils import assert_type
from tmlib.utils import notimplemented
from tmlib.image import ChannelImage
from tmlib.image import PyramidTile
from tmlib.image import IllumstatsImage
from tmlib.image import IllumstatsContainer
from tmlib.metadata import ChannelImageMetadata
from tmlib.metadata import PyramidTileMetadata
from tmlib.metadata import IllumstatsImageMetadata
from tmlib.readers import DatasetReader
from tmlib.readers import ImageReader
from tmlib.writers import DatasetWriter
from tmlib.writers import ImageWriter
from tmlib.models import File, DateMixIn
from tmlib.models.status import FileUploadStatus
from tmlib.models.utils import remove_location_upon_delete
from tmlib.models import distribute_by_hash
from tmlib.models import distribute_by_replication

logger = logging.getLogger(__name__)


@remove_location_upon_delete
@distribute_by_hash('id')
class MicroscopeImageFile(File, DateMixIn):

    '''Image file that was generated by the microscope.
    The file format differs between microscope types and may be vendor specific.

    Attributes
    ----------
    name: str
        name of the file
    omexml: lxml.etree._Element
        OMEXML metadata
    acquisition_id: int
        ID of the parent acquisition
    acquisition: tmlib.acquisition.Acquisition
        parent acquisition to which the file belongs
    '''

    #: str: name of the corresponding database table
    __tablename__ = 'microscope_image_files'

    __table_args__ = (UniqueConstraint('name', 'acquisition_id'), )

    # Table columns
    name = Column(String, index=True)
    omexml = Column(Text)
    status = Column(String, index=True)
    acquisition_id = Column(
        Integer,
        ForeignKey('acquisitions.id', onupdate='CASCADE', ondelete='CASCADE'),
        index=True
    )

    # Relationships to other tables
    acquisition = relationship(
        'Acquisition',
        backref=backref('microscope_image_files', cascade='all, delete-orphan')
    )

    def __init__(self, name, acquisition_id):
        '''
        Parameters
        ----------
        name: str
            name of the microscope image file
        acquisition_id: int
            ID of the parent acquisition
        '''
        self.name = name
        self.acquisition_id = acquisition_id
        self.status = FileUploadStatus.WAITING

    @property
    def location(self):
        '''str: location of the file'''
        return os.path.join(
            self.acquisition.microscope_images_location, self.name
        )

    @notimplemented
    def get(self):
        pass

    @notimplemented
    def put(self, data):
        pass

    def as_dict(self):
        '''
        Return attributes as key-value pairs.

        Returns
        -------
        dict
        '''
        return {
            'id': self.id,
            'name': self.name,
            'status': self.status
        }

    def __repr__(self):
        return '<MicroscopeImageFile(id=%r, name=%r)>' % (self.id, self.name)


@remove_location_upon_delete
@distribute_by_hash('id')
class MicroscopeMetadataFile(File, DateMixIn):

    '''Metadata file that was generated by the microscope.
    The file format differs between microscope types and may be vendor specific.

    Attributes
    ----------
    name: str
        name of the file
    acquisition_id: int
        ID of the parent acquisition
    acquisition: tmlib.acquisition.Acquisition
        parent acquisition to which the file belongs
    '''

    #: str: name of the corresponding database table
    __tablename__ = 'microscope_metadata_files'

    __table_args__ = (UniqueConstraint('name', 'acquisition_id'), )

    # Table columns
    name = Column(String, index=True)
    status = Column(String, index=True)
    acquisition_id = Column(
        Integer,
        ForeignKey('acquisitions.id', onupdate='CASCADE', ondelete='CASCADE'),
        index=True
    )

    # Relationships to other tables
    acquisition = relationship(
        'Acquisition',
        backref=backref(
            'microscope_metadata_files', cascade='all, delete-orphan'
        )
    )

    def __init__(self, name, acquisition_id):
        '''
        Parameters
        ----------
        name: str
            name of the file
        acquisition_id: int
            ID of the parent acquisition
        '''
        self.name = name
        self.acquisition_id = acquisition_id
        self.status = FileUploadStatus.WAITING

    @property
    def location(self):
        '''str: location of the file'''
        return os.path.join(
            self.acquisition.microscope_metadata_location, self.name
        )

    @notimplemented
    def get(self):
        pass

    @notimplemented
    def put(self, data):
        pass

    def as_dict(self):
        '''Return attributes as key-value pairs.

        Returns
        -------
        dict
        '''
        return {
            'id': self.id,
            'name': self.name,
            'status': self.status
        }

    def __repr__(self):
        return '<MicroscopeMetdataFile(id=%r, name=%r)>' % (self.id, self.name)


@remove_location_upon_delete
@distribute_by_hash('id')
class ChannelImageFile(File, DateMixIn):

    '''A *channel image file* holds a single 2D pixels plane that was extracted
    from a microscope image file. It represents a unique combination of
    time point, site, and channel.

    Attributes
    ----------
    tpoint: int
        zero-based time point index in the time series
    omitted: bool
        whether the image file is considered empty, i.e. consisting only of
        background pixels without having biologically relevant information
    site_id: int
        ID of the parent site
    site: tmlib.models.Site
        parent site to which the image file belongs
    cycle_id: int
        ID of the parent cycle
    cycle: tmlib.models.Cycle
        parent cycle to which the image file belongs
    channel_id: int
        ID of the parent channel
    channel: tmlib.models.Channel
        parent channel to which the image file belongs
    n_planes: int
        number of z-resolution levels
    '''

    #: str: name of the corresponding database table
    __tablename__ = 'channel_image_files'

    __table_args__ = (
        UniqueConstraint('tpoint', 'site_id', 'cycle_id', 'channel_id'),
    )

    # Table columns
    _name = Column('name', String, index=True)
    name = Column(String, index=True)
    tpoint = Column(Integer, index=True)
    omitted = Column(Boolean, index=True)
    _n_planes = Column('n_planes', Integer, index=True)
    n_planes = Column(Integer, index=True)
    cycle_id = Column(
        Integer,
        ForeignKey('cycles.id', onupdate='CASCADE', ondelete='CASCADE'),
        index=True
    )
    site_id = Column(
        Integer,
        ForeignKey('sites.id', onupdate='CASCADE', ondelete='CASCADE'),
        index=True
    )
    channel_id = Column(
        Integer,
        ForeignKey('channels.id', onupdate='CASCADE', ondelete='CASCADE'),
        index=True
    )

    # Relationships to other tables
    cycle = relationship(
        'Cycle',
        backref=backref('channel_image_files', cascade='all, delete-orphan')
    )
    site = relationship(
        'Site',
        backref=backref('channel_image_files', cascade='all, delete-orphan')
    )
    channel = relationship(
        'Channel',
        backref=backref('image_files', cascade='all, delete-orphan')
    )

    #: Format string for filenames
    FILENAME_FORMAT = 'channel_image_t{t:0>3}_{w}_y{y:0>3}_x{x:0>3}_c{c:0>3}.h5'

    def __init__(self, tpoint, site_id, cycle_id, channel_id, omitted=False):
        '''
        Parameters
        ----------
        tpoint: int
            zero-based time point index in the time series
        site_id: int
            ID of the parent site
        cycle_id: int
            ID of the parent cycle
        channel_id: int
            ID of the parent channel
        omitted: bool, optional
            whether the image file is considered empty, i.e. consisting only of
            background pixels without having biologically relevant information
            (default: ``False``)
        n_planes: int
            number of pixels planes in the image
        '''
        self.tpoint = tpoint
        self.site_id = site_id
        self.omitted = omitted
        self.cycle_id = cycle_id
        self.channel_id = channel_id
        self._n_planes = 0

    def get(self, z=None):
        '''Gets stored image.

        Parameters
        ----------
        z: int, optional
            zero-based z index of an individual pixel plane (default: ``None``)

        Returns
        -------
        tmlib.image.ChannelImage
            image stored in the file
        '''
        logger.debug('get data from channel image file: %s', self.name)
        metadata = ChannelImageMetadata(
            name=self.name,
            tpoint=self.tpoint,
            channel=self.channel.index,
            plate=self.site.well.plate.name,
            well=self.site.well.name,
            y=self.site.y,
            x=self.site.x,
            cycle=self.cycle.index
        )
        if z is not None:
            with DatasetReader(self.location) as f:
                array = f.read('z_%d' % z)
            metadata.zplane = z
        else:
            pixels = list()
            with DatasetReader(self.location) as f:
                datasets = f.list_datasets(pattern='z_\d+')
                for z in datasets:
                    pixels.append(f.read(z))
            array = np.dstack(pixels)
        if self.site.intersection is not None:
            metadata.upper_overhang = self.site.intersection.upper_overhang
            metadata.lower_overhang = self.site.intersection.lower_overhang
            metadata.right_overhang = self.site.intersection.right_overhang
            metadata.left_overhang = self.site.intersection.left_overhang
            shift = [
                s for s in self.site.shifts if s.cycle_id == self.cycle_id
            ][0]
            metadata.x_shift = shift.x
            metadata.y_shift = shift.y
        return ChannelImage(array, metadata)

    @assert_type(image='tmlib.image.ChannelImage')
    def put(self, image, z=None):
        '''Puts image to storage.

        Parameters
        ----------
        image: tmlib.image.ChannelImage
            pixels/voxels data that should be stored in the image file
        z: int, optional
            zero-based z index of an individual pixel plane (default: ``None``)

        Note
        ----
        When no `z` index is provided, the file will be truncated and all
        planes replaced.
        '''
        logger.debug('put data to channel image file: %s', self.name)
        if z is not None:
            if image.dimensions[2] > 1:
                raise ValueError('Image must be a 2D pixels plane.')
            with DatasetWriter(self.location) as f:
                f.write('z_%d' % z, image.array)
                self.n_planes = len(f.list_datasets(pattern='z_\d+'))
        else:
            with DatasetWriter(self.location, truncate=True) as f:
                for z, plane in image.iter_planes():
                    f.write('z_%d' % z, plane.array)
            self.n_planes = image.dimensions[2]

    @hybrid_property
    def name(self):
        '''str: name of the file'''
        if self._name is None:
            self._name = self.FILENAME_FORMAT.format(
                t=self.tpoint, w=self.site.well.name,
                y=self.site.y, x=self.site.x,
                c=self.channel.index
            )
        return self._name

    @hybrid_property
    def n_planes(self):
        '''int: number of planes stored in the file'''
        return self._n_planes

    @n_planes.setter
    def n_planes(self, value):
        self._n_planes = value

    @property
    def location(self):
        '''str: location of the file'''
        return os.path.join(self.cycle.channel_images_location, self.name)

    def __repr__(self):
        return (
            '<ChannelImageFile('
                'id=%r, tpoint=%r, well=%r, y=%r, x=%r, channel=%r'
            ')>'
            % (self.id, self.tpoint, self.site.well.name, self.site.y,
               self.site.x, self.channel.index)
        )


# @remove_location_upon_delete
# @distribute_by_hash('id')
# class ProbabilityImageFile(File, DateMixIn):

#     '''A *probability image file* holds a single 2D pixels plane that was extracted
#     from a microscope image file.

#     Attributes
#     ----------
#     name: str
#         name of the file
#     tpoint: int
#         zero-based time point index in the time series
#     site_id: int
#         ID of the parent site
#     site: tmlib.models.Site
#         parent site to which the image file belongs
#     mapobject_type_id: int
#         ID of the parent mapobject type
#     mapobject_type: tmlib.models.MapobjectType
#         parent channel to which the image file belongs
#     '''

#     #: str: name of the corresponding database table
#     __tablename__ = 'probability_image_files'

#     __table_args__ = (
#         UniqueConstraint('tpoint', 'site_id', 'mapobject_type_id'),
#     )

#     # Table columns
#     name = Column(String, index=True)
#     tpoint = Column(Integer, index=True)
#     site_id = Column(Integer, ForeignKey('sites.id'))
#     mapobject_type_id = Column(
#         Integer,
#         ForeignKey('mapobject_types.id', onupdate='CASCADE', ondelete='CASCADE')
#     )

#     # Relationships to other tables
#     site = relationship(
#         'Site',
#         backref=backref(
#             'probability_image_files', cascade='all, delete-orphan'
#         )
#     )
#     mapobject_type = relationship(
#         'MapobjectType',
#         backref=backref(
#             'probability_image_files', cascade='all, delete-orphan'
#         )
#     )

#     FILENAME_FORMAT = 'probability_image_t{t:0>3}_{w}_y{y:0>3}_x{x:0>3}_m{m:0>3}.tif'

#     def __init__(self, tpoint, site_id, mapobject_type_id):
#         '''
#         Parameters
#         ----------
#         tpoint: int
#             zero-based time point index in the time series
#         site_id: int
#             ID of the parent site
#         site: tmlib.models.Site
#             parent site to which the image file belongs
#         mapobject_type_id: int
#             ID of the parent mapobject type
#         '''
#         self.tpoint = tpoint
#         self.site_id = site_id
#         self.mapobject_type_id = mapobject_type_id
#         self.name = self.FILENAME_FORMAT.format(
#             t=self.tpoint, w=self.site.well, y=self.site.y, x=self.site.x,
#             m=self.mapobject_type_id
#         )

#     def get(self):
#         '''Get image from store.

#         Returns
#         -------
#         tmlib.image.ProbabilityImage
#             image stored in the file
#         '''
#         # TODO
#         logger.debug('get data from probability image file: %s', self.name)
#         with ImageReader(self.location) as f:
#             pixels = f.read()
#         # metadata = ProbabilityImageMetadata(
#         #     name=self.name,
#         #     tpoint=self.tpoint,
#         #     zplane=self.zplane,
#         #     mapobject_type_id=self.mapobject_type_id,
#         #     site_id=self.site_id,
#         # )
#         metadata = None
#         return ProbabilityImage(pixels, metadata)

#     @assert_type(image='tmlib.image.ProbabilityImage')
#     def put(self, image):
#         '''Put image to store.

#         Parameters
#         ----------
#         image: tmlib.image.ProbabilityImage
#             data that should be stored in the image file
#         '''
#         logger.debug('put data to probability image file: %s', self.name)
#         with ImageWriter(self.location) as f:
#             f.write(image.array)

#     @property
#     def location(self):
#         '''str: location of the file'''
#         return os.path.join(self.mapobject_type.location, self.name)

#     def __repr__(self):
#         return (
#             '<ProbabilityImageFile('
#                 'id=%r, tpoint=%r, mapobject_type=%r, well=%r, y=%r, x=%r'
#             ')>'
#             % (self.id, self.tpoint, self.mapobject_type.name,
#                self.site.well, self.site.y, self.site.x)
#         )


@remove_location_upon_delete
@distribute_by_hash('id')
class PyramidTileFile(File):

    '''A *pyramid tile file* is a component of an image pyramid. Each tile
    holds a single, small 2D 8-bit pixel plane.

    Attributes
    ----------
    name: str
        name of the file
    group: int
        zero-based tile group index
    level: int
        zero-based zoom level index
    row: int
        zero-based row index of the tile at given `level`
    column: int
        zero-based column index of the tile at given zoom `level`
    channel_layer_id: int
        ID of the parent channel pyramid
    channel_pyramid: tmlib.models.ChannelLayer
        parent channel pyramid to which the tile belongs
    '''

    #: str: name of the corresponding database table
    __tablename__ = 'pyramid_tile_files'

    __table_args__ = (
        UniqueConstraint(
            'level', 'row', 'column', 'channel_layer_id'
        ),
    )

    # Table columns
    name = Column(String, index=True)
    group = Column(Integer, index=True)
    level = Column(Integer, index=True)
    row = Column(Integer, index=True)
    column = Column(Integer, index=True)
    channel_layer_id = Column(
        Integer,
        ForeignKey('channel_layers.id', onupdate='CASCADE', ondelete='CASCADE'),
        index=True
    )

    # Relationships to other tables
    channel_layer = relationship(
        'ChannelLayer',
        backref=backref('pyramid_tile_files', cascade='all, delete-orphan')
    )

    def __init__(self, name, group, level, row, column, channel_layer_id):
        '''
        Parameters
        ----------
        name: str
            name of the file
        group: int
            zero-based tile group index
        level: int
            zero-based zoom level index
        row: int
            zero-based row index of the tile at given `level`
        column: int
            zero-based column index of the tile at given zoom `level`
        channel_layer_id: int
            ID of the parent channel pyramid
        '''
        # TODO: set name based on format string
        self.name = name
        self.group = group
        self.row = row
        self.column = column
        self.level = level
        self.channel_layer_id = channel_layer_id

    def get(self):
        '''Gets a stored tile.

        Returns
        -------
        tmlib.image.PyramidTile
            tile stored in the file
        '''
        logger.debug('get data from pyramid tile file: %s', self.name)
        with ImageReader(self.location) as f:
            pixels = f.read(dtype=np.uint8)
        metadata = PyramidTileMetadata(
            name=self.name,
            group=self.group,
            level=self.level,
            row=self.row,
            column=self.column,
            zplane=self.channel_layer.zplane
        )
        return PyramidTile(pixels, metadata)

    @assert_type(image='tmlib.image.PyramidTile')
    def put(self, image):
        '''Puts a tile to storage.

        Parameters
        ----------
        image: tmlib.image.PyramidTile
            pixels data that should be stored in the file
        '''
        logger.debug('put data to pyramid tile file: %s', self.name)
        with ImageWriter(self.location) as f:
            f.write(image.array)

    @property
    def location(self):
        '''str: location of the file'''
        return os.path.join(
            self.channel_layer.location, 'TileGroup%d' % self.group, self.name
        )

    def __repr__(self):
        return (
            '<PyramidTileFile('
                'id=%r, row=%r, column=%r, level=%r'
            ')>'
            % (self.id, self.row, self.column, self.level)
        )


@remove_location_upon_delete
@distribute_by_replication
class IllumstatsFile(File, DateMixIn):

    '''An *illumination statistics file* holds matrices for mean and standard
    deviation values calculated at each pixel position across all images of
    the same *channel* and *cycle*.

    Attributes
    ----------
    name: str
        name of the file
    channel_id: int
        ID of the parent channel
    channel: tmlib.models.Channel
        parent channel to which the image file belongs
    cycle_id: int
        ID of the parent cycle
    cycle: tmlib.models.Cycle
        parent cycle to which the image file belongs
    '''

    #: str: format string to build filename
    FILENAME_FORMAT = 'illumstats_{channel_id}.h5'

    #: str: name of the corresponding database table
    __tablename__ = 'illumstats_files'

    __table_args__ = (UniqueConstraint('channel_id', 'cycle_id'), )

    # Table columns
    name = Column(String, index=True)
    channel_id = Column(
        Integer,
        ForeignKey('channels.id', onupdate='CASCADE', ondelete='CASCADE'),
        index=True
    )
    cycle_id = Column(
        Integer,
        ForeignKey('cycles.id', onupdate='CASCADE', ondelete='CASCADE'),
        index=True
    )

    # Relationships to other tables
    channel = relationship(
        'Channel',
        backref=backref('illumstats_files', cascade='all, delete-orphan')
    )
    cycle = relationship(
        'Cycle',
        backref=backref('illumstats_files', cascade='all, delete-orphan')
    )

    def __init__(self, channel_id, cycle_id):
        '''
        Parameters
        ----------
        channel_id: int
            ID of the parent channel
        cycle_id: int
            ID of the parent cycle

        Raises
        ------
        ValueError
            when `name` doesn't match pattern specified by
            :py:attribute:`tmlib.files.ILLUMSTATS_FILENAME_FORMAT`
        '''
        self.channel_id = channel_id
        self.cycle_id = cycle_id
        self.name = self.FILENAME_FORMAT.format(
            channel_id=self.channel_id
        )

    def get(self):
        '''Get illumination statistics images from store.

        Returns
        -------
        Illumstats
            illumination statistics images
        '''
        logger.debug(
            'get data from illumination statistics file: %s', self.name
        )
        metadata = IllumstatsImageMetadata(
            channel=self.channel.index,
            cycle=self.cycle.index
        )
        with DatasetReader(self.location) as f:
            mean = IllumstatsImage(f.read('mean'), metadata)
            std = IllumstatsImage(f.read('std'), metadata)
            keys = f.read('percentiles/keys')
            values = f.read('percentiles/values')
            percentiles = dict(zip(keys, values))
        return IllumstatsContainer(mean, std, percentiles).smooth()

    @assert_type(data='tmlib.image.IllumstatsContainer')
    def put(self, data):
        '''Put illumination statistics images to store.

        Parameters
        ----------
        data: IllumstatsContainer
            illumination statistics
        '''
        logger.debug('put data to illumination statistics file: %s', self.name)
        with DatasetWriter(self.location, truncate=True) as f:
            f.write('mean', data.mean.array)
            f.write('std', data.std.array)
            f.write('/percentiles/keys', data.percentiles.keys())
            f.write('/percentiles/values', data.percentiles.values())

    @property
    def location(self):
        '''str: location of the file'''
        return os.path.join(self.cycle.illumstats_location, self.name)

    def __repr__(self):
        return (
            '<IllumstatsFile(id=%r, channel=%r)>'
            % (self.id, self.channel_id)
        )
