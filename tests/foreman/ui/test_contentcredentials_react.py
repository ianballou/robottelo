"""Test class for Content Credentials React UI

Tests for the React-based content credentials details page, covering
CRUD operations, tab navigation, inline editing, and association
verification for products, repositories, and alternate content sources.

:Requirement: ContentCredentials

:CaseAutomation: Automated

:CaseComponent: ContentCredentials

:team: Artemis

:CaseImportance: High

"""

import pytest

from robottelo.config import settings
from robottelo.constants import CONTENT_CREDENTIALS_TYPES, DataFile
from robottelo.utils.datafactory import gen_string


@pytest.fixture(scope='module')
def gpg_content():
    return DataFile.VALID_GPG_KEY_FILE.read_text()


@pytest.fixture(scope='module')
def gpg_path():
    return DataFile.VALID_GPG_KEY_FILE


@pytest.fixture
def gpg_key_with_product(target_sat, module_org, gpg_content):
    """Create a GPG key associated with a product that has one repository."""
    gpg_key = target_sat.api.GPGKey(
        content=gpg_content,
        name=gen_string('alpha'),
        organization=module_org,
    ).create()
    product = target_sat.api.Product(
        gpg_key=gpg_key,
        organization=module_org,
    ).create()
    repo = target_sat.api.Repository(
        product=product,
        url=settings.repos.yum_1.url,
    ).create()
    return {
        'gpg_key': gpg_key,
        'product': product,
        'repo': repo,
    }


# ========================================================================
# CRUD Operations
# ========================================================================


@pytest.mark.e2e
@pytest.mark.upgrade
def test_positive_end_to_end_react(session, target_sat, module_org, gpg_content):
    """Perform end-to-end CRUD testing for content credentials via the React UI.

    :id: f3a1b2c4-d5e6-4a7b-8c9d-0e1f2a3b4c5d

    :steps:
        1. Create a new GPG key content credential with valid content
        2. Search for the created credential and verify it appears
        3. Associate a product and repository with the credential via API
        4. Read credential details and verify all fields and tabs
        5. Update the credential name via inline editing
        6. Verify the name change persists
        7. Clean up product/repo dependencies
        8. Delete the credential
        9. Verify the credential is removed

    :expectedresults: All CRUD operations succeed and data is consistent
        across the details page tabs.
    """
    name = gen_string('alpha')
    new_name = gen_string('alpha')
    with session:
        # Create new GPG key with valid content
        session.contentcredential.create(
            {
                'name': name,
                'content_type': CONTENT_CREDENTIALS_TYPES['gpg'],
                'content': gpg_content,
            }
        )
        assert session.contentcredential.search(name)[0]['Name'] == name

        # Associate product and repo via API
        gpg_key = target_sat.api.ContentCredential(organization=module_org).search(
            query={'search': f'name="{name}"'}
        )[0]
        product = target_sat.api.Product(gpg_key=gpg_key, organization=module_org).create()
        repo = target_sat.api.Repository(product=product).create()

        # Read and verify details tab
        values = session.contentcredential.read(name)
        assert values['details']['name'] == name
        assert values['details']['content_type'] == CONTENT_CREDENTIALS_TYPES['gpg']
        assert values['details']['products'] == '1'
        assert values['details']['repos'] == '1'

        # Verify products tab
        assert len(values['products']['table']) == 1
        assert values['products']['table'][0]['Name'] == product.name

        # Verify repositories tab
        assert len(values['repositories']['table']) == 1
        assert values['repositories']['table'][0]['Name'] == repo.name

        # Update name
        session.contentcredential.update(name, {'details.name': new_name})
        assert session.contentcredential.search(new_name)[0]['Name'] == new_name

        # Clean up and delete
        repo.delete()
        product.delete()
        session.contentcredential.delete(new_name)
        assert session.contentcredential.search(new_name)[0]['Name'] != new_name


def test_positive_create_with_file_upload(session, gpg_path):
    """Create a content credential by uploading a GPG key file.

    :id: a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d

    :steps:
        1. Navigate to content credentials creation page
        2. Create a credential using file upload
        3. Search for the created credential

    :expectedresults: Content credential is created successfully via file upload.
    """
    name = gen_string('alpha')
    with session:
        session.contentcredential.create(
            {
                'name': name,
                'content_type': CONTENT_CREDENTIALS_TYPES['gpg'],
                'upload_file': gpg_path,
            }
        )
        assert session.contentcredential.search(name)[0]['Name'] == name


def test_positive_search_scoped_react(session, target_sat, gpg_content, module_org):
    """Search for a content credential scoped by organization ID.

    :id: b2c3d4e5-f6a7-8b9c-0d1e-2f3a4b5c6d7e

    :customerscenario: true

    :steps:
        1. Create a content credential via the UI
        2. Search using organization_id scope

    :expectedresults: The correct credential is returned when searching
        by organization scope.

    :BZ: 1259374
    """
    name = gen_string('alpha')
    with session:
        session.organization.select(module_org.name)
        session.contentcredential.create(
            {
                'name': name,
                'content_type': CONTENT_CREDENTIALS_TYPES['gpg'],
                'content': gpg_content,
            }
        )
        assert (
            session.contentcredential.search(f'organization_id = {module_org.id}')[0]['Name']
            == name
        )


# ========================================================================
# Details Tab Validation
# ========================================================================


def test_positive_read_details_tab(session, target_sat, module_org, gpg_content):
    """Verify the details tab displays all expected fields correctly.

    :id: c3d4e5f6-a7b8-9c0d-1e2f-3a4b5c6d7e8f

    :steps:
        1. Create a GPG key via API with associated product and repo
        2. Navigate to the credential details page
        3. Read and verify all detail fields

    :expectedresults: Details tab shows correct name, type, content,
        product count, and repository count.
    """
    gpg_key = target_sat.api.GPGKey(
        content=gpg_content,
        organization=module_org,
    ).create()
    product = target_sat.api.Product(gpg_key=gpg_key, organization=module_org).create()
    target_sat.api.Repository(product=product).create()

    with session:
        values = session.contentcredential.read(gpg_key.name, widget_names='details')
        assert values['details']['name'] == gpg_key.name
        assert values['details']['content_type'] == CONTENT_CREDENTIALS_TYPES['gpg']
        assert values['details']['products'] == '1'
        assert values['details']['repos'] == '1'


def test_positive_read_content_field(session, target_sat, module_org, gpg_content):
    """Verify the content field on the details tab displays GPG key content.

    :id: d4e5f6a7-b8c9-0d1e-2f3a-4b5c6d7e8f9a

    :steps:
        1. Create a GPG key via API
        2. Read the details tab
        3. Compare the displayed content with the original

    :expectedresults: The content field displays the GPG key content,
        with whitespace normalized.
    """
    gpg_key = target_sat.api.GPGKey(
        content=gpg_content,
        organization=module_org,
    ).create()
    with session:
        values = session.contentcredential.read(gpg_key.name, widget_names='details')
        # Transform string for comparison (whitespace normalization)
        transformed = gpg_content.replace('\n', ' ').replace('  ', ' ').rstrip()
        assert values['details']['content'] == transformed


# ========================================================================
# Products Tab
# ========================================================================


def test_positive_products_tab_empty(session, target_sat, module_org, gpg_content):
    """Verify the products tab shows empty state when no products are associated.

    :id: e5f6a7b8-c9d0-1e2f-3a4b-5c6d7e8f9a0b

    :steps:
        1. Create a GPG key via API without associating products
        2. Read the products tab

    :expectedresults: Products tab indicates no products are associated.
    """
    gpg_key = target_sat.api.GPGKey(
        content=gpg_content,
        organization=module_org,
    ).create()
    with session:
        values = session.contentcredential.read(gpg_key.name)
        empty_message = (
            "You currently don't have any Products associated with this Content Credential."
        )
        assert values['products']['table'][0]['Name'] == empty_message


def test_positive_products_tab_with_product(session, target_sat, module_org, gpg_content):
    """Verify the products tab shows an associated product.

    :id: f6a7b8c9-d0e1-2f3a-4b5c-6d7e8f9a0b1c

    :steps:
        1. Create a GPG key via API
        2. Create a product associated with the GPG key
        3. Read the products tab

    :expectedresults: Products tab displays the associated product with
        the correct usage type.
    """
    gpg_key = target_sat.api.GPGKey(
        content=gpg_content,
        organization=module_org,
    ).create()
    product = target_sat.api.Product(gpg_key=gpg_key, organization=module_org).create()
    with session:
        values = session.contentcredential.read(gpg_key.name)
        assert len(values['products']['table']) == 1
        assert values['products']['table'][0]['Name'] == product.name
        assert values['products']['table'][0]['Used as'] == CONTENT_CREDENTIALS_TYPES['gpg']


def test_positive_products_tab_empty_product(session, target_sat, module_org, gpg_content):
    """Verify the products tab shows a product without repos.

    :id: 01a7b8c9-d0e1-2f3a-4b5c-6d7e8f9a0b1c

    :steps:
        1. Create a GPG key via API
        2. Create a product (no repos) via the UI using the GPG key
        3. Read the products tab

    :expectedresults: Products tab displays the associated empty product.
    """
    prod_name = gen_string('alpha')
    gpg_key = target_sat.api.GPGKey(content=gpg_content, organization=module_org).create()
    with session:
        session.product.create({'name': prod_name, 'gpg_key': gpg_key.name})
        values = session.contentcredential.read(gpg_key.name)
        assert len(values['products']['table']) == 1
        assert values['products']['table'][0]['Name'] == prod_name
        assert values['products']['table'][0]['Used as'] == CONTENT_CREDENTIALS_TYPES['gpg']


# ========================================================================
# Repositories Tab
# ========================================================================


@pytest.mark.skipif((not settings.robottelo.REPOS_HOSTING_URL), reason='Missing repos_hosting_url')
def test_positive_repositories_tab_with_repos(session, target_sat, module_org, gpg_content):
    """Verify the repositories tab shows associated repositories.

    :id: a7b8c9d0-e1f2-3a4b-5c6d-7e8f9a0b1c2d

    :steps:
        1. Create a GPG key via API
        2. Create a product with GPG key and two repositories
        3. Read the repositories tab

    :expectedresults: Repositories tab displays both repositories with
        correct details.
    """
    gpg_key = target_sat.api.GPGKey(
        content=gpg_content,
        organization=module_org,
    ).create()
    product = target_sat.api.Product(gpg_key=gpg_key, organization=module_org).create()
    repo1 = target_sat.api.Repository(product=product, url=settings.repos.yum_1.url).create()
    repo2 = target_sat.api.Repository(product=product, url=settings.repos.yum_2.url).create()
    with session:
        values = session.contentcredential.read(gpg_key.name)
        assert len(values['repositories']['table']) == 2
        repo_names = {repo['Name'] for repo in values['repositories']['table']}
        assert {repo1.name, repo2.name} == repo_names


@pytest.mark.skipif((not settings.robottelo.REPOS_HOSTING_URL), reason='Missing repos_hosting_url')
def test_positive_repositories_tab_details(session, target_sat, module_org, gpg_content):
    """Verify repository details shown in the repositories tab.

    :id: b8c9d0e1-f2a3-4b5c-6d7e-8f9a0b1c2d3e

    :steps:
        1. Create a GPG key via API
        2. Create a product and associate GPG key via UI
        3. Read the repositories tab and check columns

    :expectedresults: Repository entries show Name, Product, Type,
        and Used-as columns correctly.
    """
    name = gen_string('alpha')
    gpg_key = target_sat.api.GPGKey(
        content=gpg_content, name=name, organization=module_org
    ).create()
    product = target_sat.api.Product(organization=module_org).create()
    repo = target_sat.api.Repository(url=settings.repos.yum_1.url, product=product).create()
    with session:
        # Associate GPG key with the product
        session.product.update(product.name, {'details.gpg_key': gpg_key.name})
        values = session.contentcredential.read(name)
        assert len(values['repositories']['table']) == 1
        repo_row = values['repositories']['table'][0]
        assert repo_row['Name'] == repo.name
        assert repo_row['Product'] == product.name
        assert repo_row['Type'] == 'yum'
        assert repo_row['Used as'] == CONTENT_CREDENTIALS_TYPES['gpg']


@pytest.mark.skipif((not settings.robottelo.REPOS_HOSTING_URL), reason='Missing repos_hosting_url')
def test_positive_repo_level_gpg_not_on_product_tab(
    session, target_sat, module_org, gpg_content
):
    """Associate GPG key at the repository level only, not the product level.

    :id: c9d0e1f2-a3b4-5c6d-7e8f-9a0b1c2d3e4f

    :steps:
        1. Create a GPG key via API
        2. Create a product without GPG key
        3. Create a repository with the GPG key under that product
        4. Read the credential details

    :expectedresults: Products tab shows no association, but repositories
        tab shows the repository.
    """
    empty_message = (
        "You currently don't have any Products associated with this Content Credential."
    )
    name = gen_string('alpha')
    gpg_key = target_sat.api.GPGKey(
        content=gpg_content, name=name, organization=module_org
    ).create()
    product = target_sat.api.Product(organization=module_org).create()
    repo = target_sat.api.Repository(
        url=settings.repos.yum_1.url, product=product, gpg_key=gpg_key
    ).create()
    with session:
        values = session.contentcredential.read(name)
        assert values['products']['table'][0]['Name'] == empty_message
        assert len(values['repositories']['table']) == 1
        assert values['repositories']['table'][0]['Name'] == repo.name
        assert values['repositories']['table'][0]['Product'] == product.name


@pytest.mark.skipif((not settings.robottelo.REPOS_HOSTING_URL), reason='Missing repos_hosting_url')
def test_positive_repo_from_product_with_multiple_repos(
    session, target_sat, module_org, gpg_content
):
    """Associate GPG key with one repo in a multi-repo product.

    :id: d0e1f2a3-b4c5-6d7e-8f9a-0b1c2d3e4f5a

    :steps:
        1. Create a GPG key via API
        2. Create a product without GPG key
        3. Create repo1 with GPG key, repo2 without
        4. Read the credential details

    :expectedresults: Only the repo with the GPG key appears on the
        repositories tab. Product tab shows empty.
    """
    empty_message = (
        "You currently don't have any Products associated with this Content Credential."
    )
    name = gen_string('alpha')
    gpg_key = target_sat.api.GPGKey(
        content=gpg_content, name=name, organization=module_org
    ).create()
    product = target_sat.api.Product(organization=module_org).create()
    repo1 = target_sat.api.Repository(
        url=settings.repos.yum_1.url, product=product, gpg_key=gpg_key
    ).create()
    target_sat.api.Repository(url=settings.repos.yum_2.url, product=product).create()
    with session:
        values = session.contentcredential.read(name)
        assert values['products']['table'][0]['Name'] == empty_message
        assert len(values['repositories']['table']) == 1
        assert values['repositories']['table'][0]['Name'] == repo1.name


# ========================================================================
# Alternate Content Sources Tab
# ========================================================================


def test_positive_acs_tab_empty(session, target_sat, module_org, gpg_content):
    """Verify the alternate content sources tab renders when no ACS are associated.

    :id: e1f2a3b4-c5d6-7e8f-9a0b-1c2d3e4f5a6b

    :steps:
        1. Create a GPG key via API
        2. Navigate to the credential details
        3. Read the alternate content sources tab

    :expectedresults: The ACS tab loads without error, showing an empty state.
    """
    gpg_key = target_sat.api.GPGKey(
        content=gpg_content,
        organization=module_org,
    ).create()
    with session:
        values = session.contentcredential.read(gpg_key.name)
        assert 'alternate_content_sources' in values


# ========================================================================
# Inline Editing / Update Operations
# ========================================================================


def test_positive_update_name(session, target_sat, module_org, gpg_content):
    """Update the name of a content credential via inline editing.

    :id: f2a3b4c5-d6e7-8f9a-0b1c-2d3e4f5a6b7c

    :steps:
        1. Create a GPG key via API
        2. Navigate to the credential details page
        3. Edit the name inline
        4. Verify the new name is displayed

    :expectedresults: Name is updated and reflected in the list and
        details views.
    """
    name = gen_string('alpha')
    new_name = gen_string('alpha')
    gpg_key = target_sat.api.GPGKey(
        content=gpg_content, name=name, organization=module_org
    ).create()
    product = target_sat.api.Product(gpg_key=gpg_key, organization=module_org).create()
    with session:
        session.contentcredential.update(name, {'details.name': new_name})
        values = session.contentcredential.read(new_name)
        assert values['details']['name'] == new_name
        # Verify product association survives the rename
        assert len(values['products']['table']) == 1
        assert values['products']['table'][0]['Name'] == product.name


@pytest.mark.skipif((not settings.robottelo.REPOS_HOSTING_URL), reason='Missing repos_hosting_url')
def test_positive_update_name_preserves_repo_associations(
    session, target_sat, module_org, gpg_content
):
    """Updating the credential name preserves product and repository associations.

    :id: 03b4c5d6-e7f8-9a0b-1c2d-3e4f5a6b7c8d

    :steps:
        1. Create a GPG key with product and repo via API
        2. Update the credential name
        3. Read the details and verify associations persist

    :expectedresults: Product and repository associations are preserved
        after name update.
    """
    name = gen_string('alpha')
    new_name = gen_string('alpha')
    gpg_key = target_sat.api.GPGKey(
        content=gpg_content, name=name, organization=module_org
    ).create()
    product = target_sat.api.Product(gpg_key=gpg_key, organization=module_org).create()
    repo = target_sat.api.Repository(product=product, url=settings.repos.yum_1.url).create()
    with session:
        session.contentcredential.update(name, {'details.name': new_name})
        values = session.contentcredential.read(new_name)
        assert len(values['products']['table']) == 1
        assert values['products']['table'][0]['Name'] == product.name
        assert len(values['repositories']['table']) == 1
        assert values['repositories']['table'][0]['Name'] == repo.name


@pytest.mark.skipif((not settings.robottelo.REPOS_HOSTING_URL), reason='Missing repos_hosting_url')
def test_positive_update_name_preserves_repo_only_association(
    session, target_sat, module_org, gpg_content
):
    """Updating the credential name preserves repo-only GPG association.

    :id: 14c5d6e7-f8a9-0b1c-2d3e-4f5a6b7c8d9e

    :steps:
        1. Create GPG key and associate it with a repo but not its product
        2. Update the credential name
        3. Verify products tab is still empty but repo association remains

    :expectedresults: After update, GPG key is still not on the product
        but still associated with the repository.
    """
    empty_message = (
        "You currently don't have any Products associated with this Content Credential."
    )
    name = gen_string('alpha')
    new_name = gen_string('alpha')
    gpg_key = target_sat.api.GPGKey(
        content=gpg_content, name=name, organization=module_org
    ).create()
    product = target_sat.api.Product(organization=module_org).create()
    repo = target_sat.api.Repository(
        gpg_key=gpg_key, product=product, url=settings.repos.yum_1.url
    ).create()
    with session:
        session.contentcredential.update(name, {'details.name': new_name})
        values = session.contentcredential.read(new_name)
        assert values['products']['table'][0]['Name'] == empty_message
        assert len(values['repositories']['table']) == 1
        assert values['repositories']['table'][0]['Name'] == repo.name


@pytest.mark.upgrade
@pytest.mark.skipif((not settings.robottelo.REPOS_HOSTING_URL), reason='Missing repos_hosting_url')
def test_positive_update_name_preserves_multiple_repos(
    session, target_sat, module_org, gpg_content
):
    """Updating the credential name preserves multiple repository associations.

    :id: 25d6e7f8-a9b0-1c2d-3e4f-5a6b7c8d9e0f

    :steps:
        1. Create GPG key with a product that has two repos
        2. Update the credential name
        3. Verify both repos still appear on the repositories tab

    :expectedresults: Both repository associations are preserved after
        name update.
    """
    name = gen_string('alpha')
    new_name = gen_string('alpha')
    gpg_key = target_sat.api.GPGKey(
        content=gpg_content, name=name, organization=module_org
    ).create()
    product = target_sat.api.Product(gpg_key=gpg_key, organization=module_org).create()
    repo1 = target_sat.api.Repository(product=product, url=settings.repos.yum_1.url).create()
    repo2 = target_sat.api.Repository(product=product, url=settings.repos.yum_2.url).create()
    with session:
        session.contentcredential.update(name, {'details.name': new_name})
        values = session.contentcredential.read(new_name)
        assert len(values['repositories']['table']) == 2
        assert {repo1.name, repo2.name} == {
            repo['Name'] for repo in values['repositories']['table']
        }


@pytest.mark.upgrade
@pytest.mark.skipif((not settings.robottelo.REPOS_HOSTING_URL), reason='Missing repos_hosting_url')
def test_positive_update_name_repo_only_multi_repo_product(
    session, target_sat, module_org, gpg_content
):
    """Update GPG key name when associated at repo level in a multi-repo product.

    :id: 36e7f8a9-b0c1-2d3e-4f5a-6b7c8d9e0f1a

    :steps:
        1. Create GPG key and a product with two repos
        2. Associate GPG key only with repo1
        3. Update the credential name
        4. Verify only repo1 appears in the repositories tab

    :expectedresults: After update, GPG key is still associated with
        only the first repository, and not with the product.
    """
    empty_message = (
        "You currently don't have any Products associated with this Content Credential."
    )
    name = gen_string('alpha')
    new_name = gen_string('alpha')
    gpg_key = target_sat.api.GPGKey(
        content=gpg_content, name=name, organization=module_org
    ).create()
    product = target_sat.api.Product(organization=module_org).create()
    repo1 = target_sat.api.Repository(
        url=settings.repos.yum_1.url, product=product, gpg_key=gpg_key
    ).create()
    target_sat.api.Repository(product=product, url=settings.repos.yum_2.url).create()
    with session:
        session.contentcredential.update(name, {'details.name': new_name})
        values = session.contentcredential.read(new_name)
        assert values['products']['table'][0]['Name'] == empty_message
        assert len(values['repositories']['table']) == 1
        assert values['repositories']['table'][0]['Name'] == repo1.name


# ========================================================================
# Product Navigation from Details Page
# ========================================================================


@pytest.mark.skipif((not settings.robottelo.REPOS_HOSTING_URL), reason='Missing repos_hosting_url')
def test_positive_navigate_to_product_from_details(session, target_sat, module_org, gpg_content):
    """Navigate to a product from the content credential details page.

    :id: 47f8a9b0-c1d2-3e4f-5a6b-7c8d9e0f1a2b

    :steps:
        1. Create GPG key with an associated product and repo via API
        2. Navigate to the credential details page
        3. Click on the product name in the products tab
        4. Verify the product details page loads correctly

    :expectedresults: Clicking a product name navigates to the product
        details page showing correct GPG key association.

    :BZ: 1411800
    """
    name = gen_string('alpha')
    gpg_key = target_sat.api.GPGKey(
        content=gpg_content, name=name, organization=module_org
    ).create()
    product = target_sat.api.Product(gpg_key=gpg_key, organization=module_org).create()
    target_sat.api.Repository(url=settings.repos.yum_1.url, product=product).create()
    with session:
        values = session.contentcredential.read(gpg_key.name)
        assert len(values['products']['table']) == 1
        assert values['products']['table'][0]['Name'] == product.name
        assert len(values['repositories']['table']) == 1
        product_values = session.contentcredential.get_product_details(gpg_key.name, product.name)
        assert product_values['details']['name'] == product.name
        assert product_values['details']['gpg_key'] == gpg_key.name
        assert product_values['details']['repos_count'] == '1'


# ========================================================================
# Repo Discovery Flow
# ========================================================================


@pytest.mark.upgrade
@pytest.mark.skipif((not settings.robottelo.REPOS_HOSTING_URL), reason='Missing repos_hosting_url')
@pytest.mark.usefixtures('allow_repo_discovery')
def test_positive_update_key_for_discovered_repo(session, gpg_path):
    """Associate GPG key with a product via repo discovery, then update the key name.

    :id: 58a9b0c1-d2e3-4f5a-6b7c-8d9e0f1a2b3c

    :steps:
        1. Create a GPG key via file upload
        2. Discover repos and create a product with the GPG key
        3. Verify product/repo associations
        4. Update the GPG key name
        5. Verify associations persist after update

    :expectedresults: GPG key is associated with product and repository
        before and after the name update.

    :BZ: 1210180, 1461804
    """
    name = gen_string('alpha')
    new_name = gen_string('alpha')
    product_name = gen_string('alpha')
    repo_name = 'fakerepo01'
    with session:
        session.contentcredential.create(
            {
                'name': name,
                'content_type': CONTENT_CREDENTIALS_TYPES['gpg'],
                'upload_file': gpg_path,
            }
        )
        assert session.contentcredential.search(name)[0]['Name'] == name
        session.product.discover_repo(
            {
                'repo_type': 'Yum Repositories',
                'url': settings.repos.repo_discovery.url,
                'discovered_repos.repos': repo_name,
                'create_repo.product_type': 'New Product',
                'create_repo.product_content.product_name': product_name,
                'create_repo.product_content.gpg_key': name,
            }
        )
        values = session.contentcredential.read(name)
        assert len(values['products']['table']) == 1
        assert values['products']['table'][0]['Name'] == product_name
        assert len(values['repositories']['table']) == 1
        assert values['repositories']['table'][0]['Name'].split(' ')[-1] == repo_name
        product_values = session.product.read(product_name)
        assert product_values['details']['gpg_key'] == name

        # Update the key name
        session.contentcredential.update(name, {'details.name': new_name})
        values = session.contentcredential.read(new_name)
        assert len(values['products']['table']) == 1
        assert values['products']['table'][0]['Name'] == product_name
        assert len(values['repositories']['table']) == 1
        assert values['repositories']['table'][0]['Name'].split(' ')[-1] == repo_name
        product_values = session.product.read(product_name)
        assert product_values['details']['gpg_key'] == new_name


# ========================================================================
# Association via UI (product update to add GPG key)
# ========================================================================


@pytest.mark.skipif((not settings.robottelo.REPOS_HOSTING_URL), reason='Missing repos_hosting_url')
def test_positive_associate_gpg_via_product_update(
    session, target_sat, module_org, gpg_content
):
    """Associate a GPG key with a product via the product edit page.

    :id: 69b0c1d2-e3f4-5a6b-7c8d-9e0f1a2b3c4d

    :steps:
        1. Create a GPG key and product with repo via API (no GPG on product)
        2. Update the product to add GPG key via UI
        3. Verify the credential details page reflects the association

    :expectedresults: After product update, GPG key shows the product
        and repository in its tabs.
    """
    name = gen_string('alpha')
    gpg_key = target_sat.api.GPGKey(
        content=gpg_content, name=name, organization=module_org
    ).create()
    product = target_sat.api.Product(organization=module_org).create()
    repo = target_sat.api.Repository(url=settings.repos.yum_1.url, product=product).create()
    with session:
        empty_message = (
            "You currently don't have any Products associated with this Content Credential."
        )
        values = session.contentcredential.read(name)
        assert values['products']['table'][0]['Name'] == empty_message
        # Associate GPG key with product via product edit
        session.product.update(product.name, {'details.gpg_key': gpg_key.name})
        values = session.contentcredential.read(name)
        assert len(values['products']['table']) == 1
        assert values['products']['table'][0]['Name'] == product.name
        assert len(values['repositories']['table']) == 1
        assert values['repositories']['table'][0]['Name'] == repo.name


@pytest.mark.skipif((not settings.robottelo.REPOS_HOSTING_URL), reason='Missing repos_hosting_url')
def test_positive_associate_gpg_via_repo_update(
    session, target_sat, module_org, gpg_content
):
    """Associate a GPG key with a repository via the repository edit page.

    :id: 7a0c1d2e-f3a4-5b6c-7d8e-9f0a1b2c3d4e

    :steps:
        1. Create a GPG key and product with repo via API (no GPG on either)
        2. Update the repository to add GPG key via UI
        3. Verify the credential details page shows repo but not product

    :expectedresults: After repo update, GPG key shows only the repository
        (not the product) in its tabs.
    """
    empty_message = (
        "You currently don't have any Products associated with this Content Credential."
    )
    name = gen_string('alpha')
    gpg_key = target_sat.api.GPGKey(
        content=gpg_content, name=name, organization=module_org
    ).create()
    product = target_sat.api.Product(organization=module_org).create()
    repo = target_sat.api.Repository(url=settings.repos.yum_1.url, product=product).create()
    with session:
        values = session.contentcredential.read(name)
        assert values['products']['table'][0]['Name'] == empty_message
        # Associate GPG key with repository
        session.repository.update(product.name, repo.name, {'repo_content.gpg_key': gpg_key.name})
        values = session.contentcredential.read(name)
        assert values['products']['table'][0]['Name'] == empty_message
        assert len(values['repositories']['table']) == 1
        assert values['repositories']['table'][0]['Name'] == repo.name
        assert values['repositories']['table'][0]['Product'] == product.name
