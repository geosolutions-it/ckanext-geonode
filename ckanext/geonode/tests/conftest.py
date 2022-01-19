import pytest

from ckan.model import Package, Group, PackageExtra, meta, GroupExtra, Member, PackageTag
from ckanext.harvest.model import HarvestObject, HarvestObjectError


@pytest.fixture
def remove_dataset_groups():
    for cls in (
        HarvestObjectError,
        HarvestObject,

        PackageTag,
        PackageExtra, Package,
        Member,
        GroupExtra, Group
    ):
        meta.Session.query(cls).delete()

    meta.Session.commit()
