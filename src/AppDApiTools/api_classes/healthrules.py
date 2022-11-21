import datetime
import json
import sys

from cryptography.fernet import Fernet
import requests
import logging
import argparse
from .api_base import ApiBase
from .applications import Applications

class Healthrules(ApiBase):

    @classmethod
    def get_function_parms(cls, subparser):
        # print('getFunctions')
        functions = [
            'list',
            'get',
            'suppression_list',
            'suppression_get',
            'suppression_create'
        ]
        class_commands = subparser.add_parser('Healthrules', help='Healthrules commands')
        class_commands.add_argument('function', choices=functions, help='The Healthrules api function to run')
        class_commands.add_argument('--application', help='Specific Applications id or name')
        class_commands.add_argument('--system', help='Specific system prefix config to use')
        class_commands.add_argument('--input', help='The input template created with the AppDynamics UI')
        class_commands.add_argument('--output', help='The output file.', nargs='?', const='dashboard_name')
        class_commands.add_argument('--verbose', help='Enable verbose output', action='store_true')
        class_commands.add_argument('--name', help='Health Rule name or Suppression name')
        class_commands.add_argument('--id', help='Health Rule id or Suppression id')
        class_commands.add_argument('--start', help='Suppression start time 24HR format (YYYY-MM-DD HH:MM:SS)')
        class_commands.add_argument('--duration', help='Suppression duration in minutes')
        class_commands.add_argument('--rule_list', help='Suppression rule names as quoted comma delimited list')
        class_commands.add_argument('--auth', help='The auth scheme.', choices=['key', 'user'], default='key')
        return class_commands

    @classmethod
    def run(cls, args, config):
        app = Healthrules(config, args)
        app.set_config_prefixes()
        if args.function == 'list':
            app.get_health_list()
        if args.function == 'get':
            app.get_rule()
        if args.function == 'suppression_list':
            app.get_action_suppression_list()
        if args.function == 'suppression_get':
            app.get_action_suppression()
        if args.function == 'suppression_create':
            app.create_action_suppression()

    def _get_app_data(self):
        newargs = argparse.Namespace(subparser_name='Applications',
                                     function='get',
                                     id=None,
                                     name=None,
                                     verbose=self.args.verbose,
                                     auth=self.args.auth,
                                     output=None,
                                     system=self.args.system)
        app = Applications(self.config, newargs)
        app.set_config_prefixes()
        app.set_app_arg(self.args.application)
        app_data = app.get_app()
        return app_data

    def _get_suppression_id(self, suppression_name=None):
        output_tmp = self.args.output
        self.args.output = None
        alist = self.get_action_suppression_list()
        self.args.output = output_tmp
        for action in alist:
            if suppression_name == action["name"]:
                return action["id"]

    def create_action_suppression(self):
        # POST <controller_url>/controller/alerting/rest/v1/applications/<application_id>/action-suppressions
        self.set_request_logging()
        self.do_verbose_print('Doing Action Suppression List...')
        if self.args.application is None:
            print('No application id or name specified with --application, see --help')
            sys.exit()
        app_data = self._get_app_data()
        base_url = self.config[self.CONTROLLER_SECTION]['base_url']
        action_suppression = {}
        if self.args.input is not None:
            # just load json input and post
            action_suppression = json.loads(open(self.args.input, "r").read())
        else:
            if self.args.name is None:
                print('No --input so --name is required, see --help')
                sys.exit()
            if self.args.start is None:
                print('No --input so --start is required, see --help')
                sys.exit()
            if self.args.duration is None:
                print('No --input so --duration is required, see --help')
                sys.exit()
            if self.args.rule_list is None:
                print('No --input so --rule_list is required, see --help')
                sys.exit()
            start = datetime.datetime.strptime(self.args.start, '%Y-%m-%d %H:%M:%S')
            end = start + datetime.timedelta(minutes=int(self.args.duration))
            rule_list = self.args.rule_list.split(',')
            action_suppression['name'] = self.args.name
            action_suppression["disableAgentReporting"] = False
            action_suppression["recurringSchedule"] = None
            action_suppression["suppressionScheduleType"] = "ONE_TIME"
            action_suppression["timezone"] = datetime.datetime.utcnow().astimezone().tzname()
            action_suppression["startTime"] = start.strftime('%Y-%m-%dT%H:%M:%S')
            action_suppression["endTime"] = end.strftime('%Y-%m-%dT%H:%M:%S')
            action_suppression["affects"] = {"affectedInfoType": "APPLICATION"}
            action_suppression["healthRuleScope"] = {"healthRuleScopeType": "SPECIFIC_HEALTH_RULES", "healthRules": rule_list}

            self.do_verbose_print(f'Built suppresion create json: {action_suppression}')
        headers, auth = self.set_auth_headers()
        for app in app_data:
            url = f'controller/alerting/rest/v1/applications/{app["id"]}/action-suppressions'

            try:
                # response = requests.get(url, headers=headers)
                response = requests.post(base_url + url, auth=auth, headers=headers, json=action_suppression)
                response.raise_for_status()
            except requests.exceptions.HTTPError as err:
                raise SystemExit(f'Action Suppression create call returned HTTPError: {err}')
            action_suppression_data = response.json()
            self.do_verbose_print(json.dumps(action_suppression_data)[0:200] + '...')

    def get_action_suppression(self):
        # GET <controller_url>/controller/alerting/rest/v1/applications/<application_id>/action-suppressions/{action-suppression-id}
        self.set_request_logging()
        self.do_verbose_print('Doing Action Suppression List...')
        if self.args.application is None:
            print('No application id or name specified with --application, see --help')
            sys.exit()
        app_data = self._get_app_data()
        base_url = self.config[self.CONTROLLER_SECTION]['base_url']
        if self.args.name is None and self.args.id is None:
            print('No action suppression name specified with --name or id with --id, see --help')
            sys.exit()
        if self.args.id is None:
            self.do_verbose_print('action suppression name given, getting list to get id')
            self.args.id = self._get_suppression_id(self.args.name)
        headers, auth = self.set_auth_headers()
        action_suppression_data = []
        for app in app_data:
            url = f'controller/alerting/rest/v1/applications/{app["id"]}/action-suppressions/{self.args.id}?output=JSON'

            try:
                # response = requests.get(url, headers=headers)
                response = requests.get(base_url + url, auth=auth, headers=headers)
                response.raise_for_status()
            except requests.exceptions.HTTPError as err:
                raise SystemExit(f'Action Suppression details call returned HTTPError: {err}')

            self.do_verbose_print(json.dumps(response.json())[0:200] + '...')
            action_suppression_data.append(response.json())
        json_obj = json.dumps(action_suppression_data)
        if self.args.output:
            with open(self.args.output, "w") as outfile:
                self.do_verbose_print(f'Saving exported file to {self.args.output}')
                outfile.write(json_obj)
        return action_suppression_data

    def get_action_suppression_list(self):
        # GET <controller_url>/controller/alerting/rest/v1/applications/<application_id>/action-suppressions
        self.set_request_logging()
        self.do_verbose_print('Doing Action Suppression List...')
        if self.args.application is None:
            print('No application id or name specified with --application, see --help')
            sys.exit()
        app_data = self._get_app_data()
        base_url = self.config[self.CONTROLLER_SECTION]['base_url']
        headers, auth = self.set_auth_headers()
        action_suppression_data = []
        for app in app_data:
            url = f'controller/alerting/rest/v1/applications/{app["id"]}/action-suppressions?output=JSON'
            try:
                # response = requests.get(url, headers=headers)
                response = requests.get(base_url + url, auth=auth, headers=headers)
                response.raise_for_status()
            except requests.exceptions.HTTPError as err:
                raise SystemExit(f'Action Suppression list call returned HTTPError: {err}')
            self.do_verbose_print(json.dumps(response.json())[0:200] + '...')
            action_suppression_data.append(response.json())
        json_obj = json.dumps(action_suppression_data)
        if self.args.output:
            with open(self.args.output, "w") as outfile:
                self.do_verbose_print(f'Saving exported file to {self.args.output}')
                outfile.write(json_obj)
        return action_suppression_data

    def get_health_list(self):
        # GET <controller_url>/controller/alerting/rest/v1/applications/<application_id>/health-rules
        self.set_request_logging()
        self.do_verbose_print('Doing health rule List...')
        if self.args.application is None:
            print('No application id or name specified with --application, see --help')
            sys.exit()
        app_data = self._get_app_data()
        base_url = self.config[self.CONTROLLER_SECTION]['base_url']
        headers, auth = self.set_auth_headers()
        rule_data = []
        for app in app_data:
            url = f'controller/alerting/rest/v1/applications/{app["id"]}/health-rules?output=JSON'

            try:
                #response = requests.get(url, headers=headers)
                response = requests.get(base_url+url, auth=auth, headers=headers)
                response.raise_for_status()
            except requests.exceptions.HTTPError as err:
                raise SystemExit(f'Health Rule api export call returned HTTPError: {err}')
            rule_data.append(response.json())
            self.do_verbose_print(json.dumps(response.json())[0:200] + '...')
        json_obj = json.dumps(rule_data)
        if self.args.output:
            with open(self.args.output, "w") as outfile:
                self.do_verbose_print(f'Saving exported file to {self.args.output}')
                outfile.write(json_obj)
        return rule_data

    def _get_rule_id(self, rule_name=None):
        output_tmp = self.args.output
        self.args.output = None
        rule_list = self.get_health_list()
        self.args.output = output_tmp
        for rule in rule_list:
            if rule_name == rule["name"]:
                return rule["id"]

    def get_rule(self):
        # GET <controller_url>/controller/alerting/rest/v1/applications/<application_id>/health-rules/{health-rule-id}
        self.set_request_logging()
        self.do_verbose_print('Doing health rule get...')
        if self.args.application is None:
            print('No application id or name specified with --application, see --help')
            sys.exit()
        app_data = self._get_app_data()
        self.do_verbose_print("Got App Data")
        self.do_verbose_print(app_data)
        if self.args.name is None and self.args.id is None:
            print('No health rule name specified with --name or id with --id, see --help')
            sys.exit()
        if self.args.id is None:
            self.do_verbose_print('health rule name given, getting list to get id')
            self.args.id = self._get_rule_id(self.args.name)
        base_url = self.config[self.CONTROLLER_SECTION]['base_url']
        headers, auth = self.set_auth_headers()
        rule_data = []
        for app in app_data:
            url = f'controller/alerting/rest/v1/applications/{app_data["id"]}/health-rules/{self.args.id}'

            try:
                #response = requests.get(url, headers=headers)
                response = requests.get(base_url+url, auth=auth, headers=headers)
                response.raise_for_status()
            except requests.exceptions.HTTPError as err:
                raise SystemExit(f'Health Rule api export call returned HTTPError: {err}')
            rule_data.append(response.json())
            self.do_verbose_print(json.dumps(response.json())[0:200] + '...')
        json_obj = json.dumps(rule_data)
        if self.args.output:
            with open(self.args.output, "w") as outfile:
                self.do_verbose_print(f'Saving exported file to {self.args.output}')
                outfile.write(json_obj)
        return rule_data
