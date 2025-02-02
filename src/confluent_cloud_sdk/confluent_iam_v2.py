#  SPDX-License-Identifier: GPL-2.0-only
#  Copyright 2022 John Mille <john@compose-x.io>


from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .client_factory import ConfluentClient

import json


class IamV2Object:
    """
    IAM V2 Objects class
    """

    api_v2_path = "/iam/v2"
    api_keys_path = f"{api_v2_path}/api-keys"
    services_accounts_path = f"{api_v2_path}/service-accounts"

    def __init__(
        self,
        client_factory: ConfluentClient,
        display_name: str = None,
        description: str = None,
    ):
        self._client = client_factory
        self._id = None
        self._name = display_name
        self._description = description
        self._href = None
        self.api_path = None

    @property
    def obj_id(self):
        return self._id

    @obj_id.setter
    def obj_id(self, id_value):
        self._id = id_value

    @property
    def href(self):
        if self._href:
            return self._href
        return f"{self._client.api_url}{self.api_path}/{self.obj_id}"

    @href.setter
    def href(self, url):
        self._href = url

    def list(self):
        if self.api_path:
            return self._client.get(f"{self._client.api_url}{self.api_path}")
        return None

    def read(self):
        return self._client.get(self.href)

    def update(self, description: str):
        return self._client.patch(self.href, data={"description": description})

    def delete(self):
        return self._client.delete(self.href)


class ServiceAccount(IamV2Object):
    """
    Class to manipulate Confluent cloud service account
    """

    def __init__(
        self,
        client_factory: ConfluentClient,
        obj_id: str = None,
        display_name: str = None,
        description: str = None,
    ):
        self._id = obj_id
        self._href = None
        super().__init__(client_factory, display_name, description)
        self.api_path = self.services_accounts_path
        self._api_keys = []

    def create(self):
        """
        `create <https://docs.confluent.io/cloud/current/api.html#operation/createIamV2ServiceAccount>`_
        """
        url = f"{self._client.api_url}{self.api_path}"
        if not self._description:
            description = self._name.title()
        else:
            description = self._description
        payload = {"display_name": self._name, "description": description}
        req = self._client.post(url, data=payload)
        payload = req.json()
        self._href = payload["metadata"]["self"]
        self.obj_id = payload["id"]
        return req

    def import_api_keys(self):
        url = f"{self._client.api_url}{self.api_keys_path}?owner={self.obj_id}"
        req = self._client.get(url)
        for _api_key in req.json()["data"]:
            new_key = ApiKey(
                self._client,
                obj_id=_api_key["id"],
                owner_id=self.obj_id,
                resource_id=_api_key["spec"]["resource"]["id"],
            )
            # new_key.href = _api_key["metadata"]["self"]
            self._api_keys.append(new_key)

    def set_from_read(self, display_name: str = None, account_id: str = None):
        """
        Sets the properties from lookup
        :param display_name:
        :param account_id:
        :return:
        """
        display_name = display_name if display_name else self._name
        account_id = account_id if account_id else self.obj_id
        if account_id:
            self.obj_id = account_id
            data = self.read().json()
            self._href = data["metadata"]["self"]
            self.obj_id = data["id"]
            self._description = data["description"]
            self._name = data["display_name"]
        elif not account_id and display_name:
            accounts = self.list().json()["data"]
            for _account in accounts:
                if _account["display_name"] == display_name:
                    self._href = _account["metadata"]["self"]
                    self.obj_id = _account["id"]
                    self._description = _account["description"]
                    self._name = _account["display_name"]


class ApiKey(IamV2Object):
    """
    `API Key <https://docs.confluent.io/cloud/current/api.html#section/The-Api-Keys-Model>`_
    """

    def __init__(
        self,
        client_factory: ConfluentClient,
        obj_id: str = None,
        display_name: str = None,
        description: str = None,
        owner_id: str = None,
        resource_id: str = None,
    ):
        super().__init__(client_factory, display_name, description)
        self._id = obj_id
        self._resource_id = resource_id
        self._owner_id = owner_id
        self._href = None
        self.api_path = self.api_keys_path
        self._secret = None

    @property
    def owner_id(self):
        return self._owner_id

    @property
    def resource_id(self):
        return self._resource_id

    def create(
        self,
        owner_id: str = None,
        resource_id: str = None,
        display_name: str = None,
        description: str = None,
    ):
        """
        `create <https://docs.confluent.io/cloud/current/api.html#operation/createIamV2ApiKey>`_
        """
        url = f"{self._client.api_url}{self.api_path}"
        if not owner_id and not self.owner_id:
            raise AttributeError("Owner ID must be specified")
        owner_id = owner_id if owner_id else self._owner_id
        if not resource_id and not self.resource_id:
            raise AttributeError("Resource ID must be specified")
        resource_id = resource_id if resource_id else self.resource_id
        if not display_name and not self._name:
            display_name = f"{owner_id}::{resource_id}"
        elif not display_name and self._name:
            display_name = self._name
        if not description and not self._description:
            description = display_name.replace(r"::", " ").title()
        elif not description and self._description:
            description = self._description
        payload = {
            "spec": {
                "owner": {"id": owner_id},
                "resource": {"id": resource_id},
                "display_name": display_name,
                "description": description,
            }
        }
        req = self._client.post(
            url,
            data=payload,
        )
        reply_data = req.json()
        spec = reply_data["spec"]
        self.obj_id = reply_data["id"]
        self._href = reply_data["metadata"]["self"]
        self._owner_id = spec["owner"]["id"]
        self._resource_id = spec["resource"]["id"]
        self._secret = spec["secret"]
        return req
