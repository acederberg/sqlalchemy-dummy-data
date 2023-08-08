Scope of Work
===============================================================================

The principal objective here is finish out the functionality provided by
`faker_sqlalchemy` in regards to primary and foreign keys. This is an issue
I often encounter in testing and I have already taken a few swings at it. I
do not want to make the dummy data myself and I would prefer that the data is
'random'. My final goal is something along the lines of

.. code:: python

   # import faker_sqlalchemy
   # from faker import Faker
   from sqlalchemy_dummy_data import create_dummy_base

   from . import db

   Base = create_dummy_base()
   class DataModel(Base):
      ...


   Base.create_dummies(db.engine)
