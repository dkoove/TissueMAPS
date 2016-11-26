# TmLibrary - TissueMAPS library for distibuted image analysis routines.
# Copyright (C) 2016  Markus D. Herrmann, University of Zurich and Robin Hafen
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''Database models.

A database *model* is an object-relational mapping (ORM) of Python objects
to relational database entries. A class represents a database table and class
attributes correspond to columns of that table. Each instances of the class
maps to an individual row of table.

The central organizational unit of *TissueMAPS* is an
:class:`Experiment <tmlib.models.experiment.Experiment>`. In the database,
each *experiment* is represented by a separate
`schema <https://www.postgresql.org/docs/current/static/ddl-schemas.html>`_,
which contains tables for images and related data.

There is also a "main" (or "public") schema that
holds data beyond the scope of individual *experiments*, such as credentials
of a :class:`User <tmlib.models.user.User>`) or the status of a submitted
computational :class:`Task <tmlib.models.submission.Task>`.
It further provides reference to existing *experiments*
(see :class:`ExperimentRerefence <tmlib.models.experiment.ExperimentReference>`)
and information on *experiment*-specific user permissions
(see :class:`ExperimentShare <tmlib.models.experiment.ExperimentShare>`).

*Main* and *experiment*-specific database schemas can be accessed
programmatically using :class:`MainSession <tmlib.models.utils.MainSession>` or
:class:`ExperimentSession <tmlib.models.utils.ExperimentSession>`, respectively.
These sessions provide a database transaction that bundles all enclosing
statements into an all-or-nothing operation to ensure that either all or no
changes are persisted in the database. The transaction will be automatically
committed or rolled back in case an error occurs.
The ``session`` context exposes an instance of
:class:`SQLAlchemySession <tmlib.models.utils.SQLAlchemySession>` and queries
return instances of data model classes derived from
:class:`ExperimentModel <tmlib.models.base.ExperimentModel>`:

.. code-block:: python

    import tmlib.models as tm

    with tm.utils.ExperimentSession(experiment_id=1) as session:
        plates = session.query(tm.Plates).all()
        print plates
        print plates[0].name
        print plates[0].acquisitions

Some *SQL* statements cannot be performed within a transaction. In addition,
the *ORM* comes with a performance overhead and is not optimal for inserting
or updating a large number of rows. In these situations,
:class:`MainConnection <tmlib.models.utils.MainConnection>` or
:class:`ExperimentConnection <tmlib.models.utils.ExperimentConnection>` can
be used. These classes create individual database connections and bypass the
*ORM*. They futher make use of *autocommit* mode, where each statement gets
directly committed such that all changes are immediately effective.
*Sessions* and *connections* are entirely different beasts and expose a
different interface. While *sessions* use the *ORM*, *connections* requires
raw *SQL* statements. In addition, they don't return instance of data model
classes, but light-weight instances of a
`namedtuple <https://docs.python.org/2/library/collections.html#collections.namedtuple>`_. Similar to data models, columns can be accessed via
attributes, but the objects only return the query result and have no relations
to other objects:

.. code-block:: python

    import tmlib.models as tm

    with tm.utils.ExperimentConnection(experiment_id=1) as connection:
        connection.execute('SELECT * FROM plates;')
        plates = connection.fetchall()
        print plates
        print plates[0].name

Note
----
The *session* and *connection* contexts automatically add the
experiment-specific schema to the
`search path <https://www.postgresql.org/docs/current/static/ddl-schemas.html#DDL-SCHEMAS-PATH>`_
at runtime. To access data models outside the scope of a *session* or
*connection*, you either need to set the search path manually or specify the
schema explicitly, e.g. ``SELECT * FROM experiment_1.plates``.

Note
----
Some of the data models can be distributed, i.e. the respective tables can be
sharded accross different servers to scale out the database backend over a
cluster. To this end, *TissueMAPS* uses
`Citus <https://docs.citusdata.com/en/stable/index.html>`_.
Distributed models are flagged with ``__distribute_by_replication__`` or
``__distribute_by_hash__``, which will either replicate the table
(so called "reference" table) or distribute it accross all available
database server nodes. *Citus* functionality is implemented in form of the
`dialect <http://docs.sqlalchemy.org/en/latest/dialects/>`_ named ``citus``,
which automatically distributes tables. To make use of table distribution,
you need to set the :attr:`db_driver <tmlib.config.DefaultConfig.db_driver>`
configuration variable to ``citus``. Note, however, that the extension must
have been installed on all database servers and worker nodes must have been
registered on the master node.For more details on how to set up a database
cluster, please refer to :doc:`setup_and_deployment`.

Warning
-------
Distributed tables can be accessed via the *ORM* for reading (``SELECT``) using
:class:`ExperimentSession <tmlib.models.utils.ExperimentSession>`; however,
they cannot be updated (``INSERT`` or ``UPDATE``) via the *ORM*,
because *Citus* doesn't support multi-statement transactions for distributed
tables. These tables must therefore be updated using
:class:`ExperimentConnection <tmlib.models.utils.ExperimentConnection>`.
*Citus* currently also doesn't support ``FOREIGN KEY`` constraints on
distributed tables. For consistency, distributed tables generally have no
foreign keys, even if the normal ``postgresql`` driver is used. Care must
therefore be taken when deleting objects to keep data consistent.

'''

from tmlib.models.base import MainModel, ExperimentModel
from tmlib.models.utils import MainSession, ExperimentSession
from tmlib.models.user import User
from tmlib.models.experiment import (
    Experiment, ExperimentReference, ExperimentShare
)
from tmlib.models.well import Well
from tmlib.models.channel import Channel
from tmlib.models.layer import (
    ChannelLayer, LabelLayer, ScalarLabelLayer, SupervisedClassifierLabelLayer,
    ContinuousLabelLayer, HeatmapLabelLayer
)
from tmlib.models.tile import ChannelLayerTile
from tmlib.models.mapobject import (
    MapobjectType, Mapobject, MapobjectSegmentation
)
from tmlib.models.feature import Feature, FeatureValue, LabelValue
from tmlib.models.plate import Plate
from tmlib.models.acquisition import Acquisition, ImageFileMapping
from tmlib.models.cycle import Cycle
from tmlib.models.submission import Submission, Task
from tmlib.models.site import Site
from tmlib.models.alignment import SiteShift, SiteIntersection
from tmlib.models.file import (
    MicroscopeImageFile, MicroscopeMetadataFile, ChannelImageFile,
    IllumstatsFile
)
from tmlib.models.result import ToolResult
from tmlib.models.plot import Plot
