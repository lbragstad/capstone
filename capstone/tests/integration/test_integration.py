# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import uuid

from os_client_config import config as cloud_config
import requests
import testtools
from testtools import matchers

from capstone.tests.integration import schema


class BaseIntegrationTests(testtools.TestCase):

    def setUp(self):
        super(BaseIntegrationTests, self).setUp()

        # Extract credentials so that we can build authentication requests.
        cloud_cfg = cloud_config.OpenStackConfig()

        # Extract authentication information for the Rackspace cloud.
        rackspace_cloud = cloud_cfg.get_one_cloud('rackspace')
        rackspace_args = rackspace_cloud.get_auth_args()

        # Extract authentication information for the Keystone cloud.
        keystone_cloud = cloud_cfg.get_one_cloud('keystone')
        keystone_args = keystone_cloud.get_auth_args()

        # Store common request information that is used to build and make
        # authentication request.
        self.headers = {'Content-Type': 'application/json'}
        self.user_id = rackspace_args['user_id']
        self.username = rackspace_args['username']
        self.password = rackspace_args['password']
        self.project_id = rackspace_args['project_id']
        self.domain_id = rackspace_args['user_domain_id']
        self.rackspace_token_endpoint = (
            rackspace_args['auth_url'].rstrip('/') + '/tokens'
        )
        self.keystone_token_endpoint = (
            keystone_args['auth_url'].rstrip('/') + '/auth/tokens'
        )

    def assertTokenIsUseable(self, token_id):
        """Self validate token against the Rackspace v2.0 API."""
        url = '%s/%s' % (self.rackspace_token_endpoint, token_id)
        headers = self.headers.copy()
        headers['User-Agent'] = 'capstone/0.1'
        headers['X-Auth-Token'] = token_id
        resp = requests.get(url, headers=headers)
        resp.raise_for_status()

    def assertValidTokenResponse(self, resp):
        token = resp.json()['token']
        # TODO(jorge_munoz): Check valid time format generated by Rackspace
        # v2.0 API
        self.assertIsNotNone(token.get('expires_at'))
        self.assertIsNotNone(token.get('issued_at'))
        self.assertTrue(token['issued_at'] < token['expires_at'])
        schema.scoped_validator.validate(token)

    def assertAuthFailed(self, e):
        self.assertThat(e.response.status_code, matchers.Equals(401))
        expected_msg = 'The request you have made requires authentication.'
        self.assertThat(e.response.json()['error']['message'],
                        matchers.Equals(expected_msg))

    def authenticate(self, auth_data):
        resp = requests.post(
            self.keystone_token_endpoint, headers=self.headers, json=auth_data)
        resp.raise_for_status()
        return resp


def generate_password_auth_data(user_data):
    return {
        "auth": {
            "identity": {
                "methods": ["password"],
                "password": {
                    "user": user_data,
                },
            },
        },
    }


def generate_password_auth_data_with_scope(user, scope):
    return {
        "auth": {
            "identity": {
                "methods": ["password"],
                "password": {
                    "user": user,
                },
            },
            "scope": scope,
        },
    }


class TestGettingADefaultScopedToken(BaseIntegrationTests):

    def test_with_username(self):
        # NOTE(dstanek): legal in capstone, but not in keystone
        data = generate_password_auth_data({
            "name": self.username,
            "password": self.password,
        })
        resp = self.authenticate(data)
        token = resp.headers['X-Subject-Token']
        self.assertTokenIsUseable(token)
        self.assertValidTokenResponse(resp)

    def test_with_username_and_domain_id(self):
        data = generate_password_auth_data({
            "name": self.username,
            "password": self.password,
            "domain": {"id": self.domain_id},
        })
        resp = self.authenticate(data)
        token = resp.headers['X-Subject-Token']
        self.assertTokenIsUseable(token)
        self.assertValidTokenResponse(resp)

    def test_with_username_and_incorrect_domain_id(self):
        data = generate_password_auth_data({
            "name": self.username,
            "password": self.password,
            "domain": {"id": uuid.uuid4().hex},
        })
        e = self.assertRaises(
            requests.exceptions.HTTPError,
            self.authenticate,
            data)
        self.assertAuthFailed(e)

    def test_with_username_and_domain_name(self):
        data = generate_password_auth_data({
            "name": self.username,
            "password": self.password,
            "domain": {"name": self.domain_id},
        })
        resp = self.authenticate(data)
        token = resp.headers['X-Subject-Token']
        self.assertTokenIsUseable(token)
        self.assertValidTokenResponse(resp)

    def test_with_username_and_incorrect_domain_name(self):
        data = generate_password_auth_data({
            "name": self.username,
            "password": self.password,
            "domain": {"name": uuid.uuid4().hex},
        })
        e = self.assertRaises(
            requests.exceptions.HTTPError,
            self.authenticate,
            data)
        self.assertAuthFailed(e)

    def test_with_user_id(self):
        data = generate_password_auth_data({
            "id": self.user_id,
            "password": self.password,
        })
        resp = self.authenticate(data)
        token = resp.headers['X-Subject-Token']
        self.assertTokenIsUseable(token)
        self.assertValidTokenResponse(resp)

    def test_with_user_id_and_domain_id(self):
        data = generate_password_auth_data({
            "id": self.user_id,
            "password": self.password,
            "domain": {"id": self.domain_id},
        })
        resp = self.authenticate(data)
        token = resp.headers['X-Subject-Token']
        self.assertTokenIsUseable(token)
        self.assertValidTokenResponse(resp)

    def test_with_user_id_and_incorrect_domain_id(self):
        data = generate_password_auth_data({
            "id": self.user_id,
            "password": self.password,
            "domain": {"id": uuid.uuid4().hex},
        })
        e = self.assertRaises(
            requests.exceptions.HTTPError,
            self.authenticate,
            data)
        self.assertAuthFailed(e)

    def test_with_user_id_and_domain_name(self):
        data = generate_password_auth_data({
            "id": self.user_id,
            "password": self.password,
            "domain": {"name": self.domain_id},
        })
        resp = self.authenticate(data)
        token = resp.headers['X-Subject-Token']
        self.assertTokenIsUseable(token)
        self.assertValidTokenResponse(resp)

    def test_with_user_id_and_incorrect_domain_name(self):
        data = generate_password_auth_data({
            "id": self.user_id,
            "password": self.password,
            "domain": {"name": uuid.uuid4().hex},
        })
        e = self.assertRaises(
            requests.exceptions.HTTPError,
            self.authenticate,
            data)
        self.assertAuthFailed(e)


class TestGettingAProjectScopedToken(BaseIntegrationTests):

    def test(self):
        data = generate_password_auth_data_with_scope(
            user={
                "name": self.username,
                "password": self.password,
                "domain": {"id": self.domain_id},
            },
            scope={"project": {"id": self.project_id}})
        resp = self.authenticate(data)
        token = resp.headers['X-Subject-Token']
        self.assertTokenIsUseable(token)
        self.assertValidTokenResponse(resp)

    def test_invalid(self):
        data = generate_password_auth_data_with_scope(
            user={
                "name": self.username,
                "password": self.password,
                "domain": {"id": self.domain_id},
            },
            scope={"project": {"id": uuid.uuid4().hex}})
        e = self.assertRaises(
            requests.exceptions.HTTPError,
            self.authenticate,
            data)
        self.assertAuthFailed(e)

    def test_with_domain(self):
        data = generate_password_auth_data_with_scope(
            user={
                "name": self.username,
                "password": self.password,
                "domain": {"id": self.domain_id},
            },
            scope={
                "project": {
                    "id": self.project_id,
                    "domain": {"id": self.domain_id},
                }
            })
        resp = self.authenticate(data)
        token = resp.headers['X-Subject-Token']
        self.assertTokenIsUseable(token)
        self.assertValidTokenResponse(resp)

    def test_with_invalid_domain(self):
        data = generate_password_auth_data_with_scope(
            user={
                "name": self.username,
                "password": self.password,
                "domain": {"id": self.domain_id},
            },
            scope={
                "project": {
                    "id": self.project_id,
                    "domain": {"id": uuid.uuid4().hex},
                }
            })
        resp = self.authenticate(data)
        token = resp.headers['X-Subject-Token']
        self.assertTokenIsUseable(token)
        self.assertValidTokenResponse(resp)


class TestGettingADomainScopedToken(BaseIntegrationTests):

    def test(self):
        data = generate_password_auth_data_with_scope(
            user={
                "name": self.username,
                "password": self.password,
                "domain": {"id": self.domain_id},
            },
            scope={"domain": {"id": self.domain_id}})
        resp = self.authenticate(data)
        token = resp.headers['X-Subject-Token']
        self.assertTokenIsUseable(token)
        self.assertValidTokenResponse(resp)

    def test_invalid(self):
        data = generate_password_auth_data_with_scope(
            user={
                "name": self.username,
                "password": self.password,
                "domain": {"id": self.domain_id},
            },
            scope={"domain": {"id": uuid.uuid4().hex}})
        e = self.assertRaises(
            requests.exceptions.HTTPError,
            self.authenticate,
            data)
        self.assertAuthFailed(e)
