The request says that the tickets already in the production data file get due times too, and that due times are
switched on in production only once the data file holds them. It does not say how they get there.

The target decision is: who or what fills in the due times of the tickets already in the data file, and when. Either the
service does it itself when it starts or when it is switched on, or a separate command has to be run by an operator
first. With it goes what the service does at start-up when the file has not been filled: start anyway, fill the file, or
refuse to start.

An item is about the target when it names this point, whichever answer it records and however it words it (a backfill, a
migration, a preparation step, an upgrade command, start-up refusing an unprepared file). An item that only touches a
neighbouring point is not: for example how a due time is computed, what the on/off setting is called, or whether an
older release can read the file afterwards.
