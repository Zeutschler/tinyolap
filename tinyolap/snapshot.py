from datetime import datetime

from tinyolap.utilities.hybrid_dict import HybridDict

class Snapshot:

    def __init__(self):
        self._name = ""
        self._description = ""
        self._created = datetime.min


    @property
    def description(self) -> str:
        return self._description


    @description.setter
    def description(self, value: str):
        self._description = value


    @property
    def created(self) -> datetime:
        """
        Creates a snapshot
        :return:
        """
        return self._created


    def restore(self, create_restore_point: bool = True):
        """
        Restores the database from the specific snapshot.
        If the parameter 'create_restore_point' is set to 'True' (default) then a
        safety restore point will be created. Restore points have a specific file extension
        which includes the creation date end with '.restore',
        e.g., database := 'sales.tiny', snapshot := 'sales.tiny.2022-06-12-09-15-12-781.restore'.

        Restore points get not managed by TinyOlap, you need to manage them by yourself. To
        convert a restore point bacj to a TinyOlap database, simply rename the file by
        removing the restore extension form the file name so that it ends with '.tiny' again.

        .. warning::
            Calling this method with will instantly drop the current database and
            restore the database from the snapshot. If you decide to set 'create_restore_point = False',
            then all current data will be lost.
        """
        pass


class SnapshotManager:
    """Manages snapshots of databases. This includes the inventory, creation, deletion
    and evaluation of TinyOlap database snapshots. Snapshots are just normal TinyOlap
    databases with a specific file extension which includes the creation date and ends
    with '.snapshot', e.g., database := 'sales.tiny', snapshot := 'sales.tiny.2022-06-12-09-15-12-781.snapshot'.

    The snapshot manager uses temporary files to create snapshots (ending with '.snapshot~').
    If such temporary files exist, do not use them for any purpose. They do not represent
    consistent TinyOlap databases. Such temporary files will only exist if

        * the snapshot manager currently creates a snapshot,
        * the TinyOlap  process was killed by the user.
        * TinyOlap had crashed

    Temporary snapshots get automatically cleaned up when the snapshot manager starts.

    .. warning::
        Do not let multiple running instances of TinyOlap access the same database folder
        and operate on the same databases. For such cases it is not guaranteed that
        database and snapshot management activities deliver the expected results.

    """
    def __init__(self, database, auto_update_on_access: bool = False):
        """
        Initialize the snapshot manager for a database.

        :param database: The database to manage snapshots for.
        :param auto_update_on_access: (optional) flag if snapshot manager activities
            should refresh on every access to the filesystem to ensure that all
            currently available snapshot files are reflected by the snapshot manager.
        """
        self._snapshots: HybridDict[Snapshot] = HybridDict()
        self._database = database
        self._auto_update_on_access = auto_update_on_access

    def __iter__(self):
        for snapshot in self._snapshots:
            yield snapshot

    def __len__(self):
        return len(self._snapshots)

    def __getitem__(self, item):
        return self._snapshots[item]

    def __delitem__(self, key):
        raise NotImplementedError()

    def create(self):
        """Creates a new snapshot of the database. For in-memory databases, the folder
        'snapshots', a sub folder of the default database directory, will be used to
        store and search for snapshots.
        """
        self._database.export(self._get_snapshot_folder())

    def delete(self, before_date=None, after_date=None):
        """Deletes existing snapshot of the database. If neither the parameter 'before_date'
        and 'after_date' will be defined, all existing snapshot will be deleted.

        :param before_date: (optional) if defined, all snapshots before the defined date or timestamp will be deleted.
        :param after_date: (optional) if defined, all snapshots after the defined date or timestamp will be deleted.
        """
        raise NotImplementedError()

    def _cleanup(self):
        """Cleans up residual temporary snapshot artefacts of the database, if such exist."""
        pass

    def refresh(self):
        """Refreshes the snapshot manager, by updating the inventory of snapshots from the file system."""
        pass

    def _create_snapshot_file_path(self) -> str:
        """Creates a file path to store a snapshot. The required path will be created if it not already exists."""
        return self._create_file_name()

    def _get_snapshot_folder(self) -> str:
        """Returns the snapshot folder. The snapshot folder will be created if it does not already exist."""
        return self._create_file_name()

    def _create_file_name(self, extension="snapshot"):
        """Creates a file name with timestamp and a specific extension."""
        fmt = '{file_name}.%Y-%m-%d-%H-%M-%S-%f.{extension}'
        return datetime.now().strftime(fmt).format(file_name=self._database.name, extension=extension)
