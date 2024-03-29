import json
import requests
import logging
from .api_base import ApiBase


class Synthetics(ApiBase):


    @classmethod
    def get_function_parms(cls, subparser):
        #print('getFunctions')
        functions = [
            'web_list',
            'api_list',
            'disable_web',
            'enable_web',
            'disable_api',
            'enable_api',
        ]
        class_commands = subparser.add_parser('Synthetics', help='Synthetics commands')
        class_commands.add_argument('function', choices=functions, help='The Synthetic api function to run')
        class_commands.add_argument('--name', help='Specific synthetic job name')
        class_commands.add_argument('--appkey', help='Specific appkey synthetic jobs')
        class_commands.add_argument('--verbose', help='Enable verbose output', action='store_true')
        class_commands.add_argument('--output', help='The output file.')
        class_commands.add_argument('--system', help='Specific system prefix config to use')
        return class_commands


    @classmethod
    def run(cls, args, config):
        #print('Synthetics run')

        # create instance of yourself
        synth = Synthetics(config, args)
        synth.set_config_prefixes()
        #print(args.function)
        if args.function == 'web_list':
            synth.web_get_list()
        if args.function == 'api_list':
            synth.api_get_list()
        if args.function == 'disable_web':
            synth.disable_web()
        if args.function == 'enable_web':
            synth.enable_web()
        if args.function == 'disable_api':
            synth.disable_api()
        if args.function == 'enable_api':
            synth.enable_api()

    # def __init__(self, config, args):
    #     super().__init__(config, args)

    def api_get_list(self) -> dict:
        self.set_request_logging()
        self.do_verbose_print('Initiating api synthetic get list call...')
        if self.config is None:
            return {}
        #headers = {"Authorization": "Basic "+token}
        response = requests.get(self.config['SYNTH_INFO']['synthetic_base_url']+'v1/synthetic/api/schedule', auth=(self.config['SYNTH_INFO']['eum_account_name'], self.config['SYNTH_INFO']['eum_license_key']))
        self.do_verbose_print(response.json())
        self._dump_output(response.json())

        return response.json()

    def web_get_list(self, out_file=None) -> dict:
        self.set_request_logging()
        self.do_verbose_print('Initiating web synthetic get list call...')
        if self.config is None:
            self.do_verbose_print("No config set, returning empty {}")
            return {}
        url = self.config[self.SYNTH_SECTION]['synthetic_base_url']+'v1/synthetic/schedule'
        auth = (self.config[self.SYNTH_SECTION]['eum_account_name'], self.config[self.SYNTH_SECTION]['eum_license_key'])
        response = requests.get(url, auth=auth)
        self.do_verbose_print(f'web_get_list response: {response.text}')
        self._dump_output(response.json())
        return response.json()

    def _dump_output(self, data):
        if self.args.output is not None:
            self.do_verbose_print(f'--output specified so writing out json to file {self.args.output}')
            fp = open(self.args.output, 'w')
            json.dump(data, fp)


    def web_update(self, job_data):
        self.set_request_logging()
        self.do_verbose_print('Initiating web synthetic update call...')
        jid = job_data['_id']
        job_data = json.dumps(job_data)

        url = self.config[self.SYNTH_SECTION]['synthetic_base_url']+'v1/synthetic/schedule/'+jid
        auth = (self.config[self.SYNTH_SECTION]['eum_account_name'], self.config['SYNTH_INFO']['eum_license_key'])
        headers = {'Content-type': 'application/json'}
        response = requests.put(url, auth=auth, data=job_data, headers=headers)
        self.do_verbose_print(response)
        self.do_verbose_print(response.text)

    def disable_web(self):
        print('Initiating web synthetic disable call...')
        self._enable_disable_web(False)

    def enable_web(self):
        print('Initiating web synthetic enable call...')
        self._enable_disable_web(True)

    def _enable_disable_web(self, enabled):
        web_list = self.web_get_list()
        for item in web_list['_items']:
            for k, v in item.items():
                if self.args.name:
                    #looking by name
                    if k == 'description' and v == self.args.name:
                        #update_data = {"_id": item["_id"], "userEnabled": False}
                        item["userEnabled"] = enabled
                        self.web_update(item)
                if self.args.appkey:
                    if k == 'appKey' and v == self.args.appkey:
                        # update_data = {"_id": item["_id"], "userEnabled": False}
                        item["userEnabled"] = enabled
                        self.web_update(item)

    def api_update(self, job_data):
        self.set_request_logging()
        self.do_verbose_print('Initiating api synthetic update call...')
        jid = job_data['_id']
        job_data = json.dumps(job_data)
        url = self.config[self.SYNTH_SECTION]['synthetic_base_url'] + 'v1/synthetic/api/schedule/' + jid
        auth = (self.config[self.SYNTH_SECTION]['eum_account_name'], self.config['SYNTH_INFO']['eum_license_key'])
        headers = {'Content-type': 'application/json'}
        response = requests.put(url, auth=auth, data=job_data, headers=headers)
        self.do_verbose_print(response)
        self.do_verbose_print(response.text)

    def disable_api(self):
        self.do_verbose_print('Initiating api synthetic disable call...')
        self._enable_disable_api(False)

    def enable_api(self):
        self.do_verbose_print('Initiating api synthetic enable call...')
        self._enable_disable_api(True)

    def _enable_disable_api(self, enabled):
        api_list = self.api_get_list()
        for item in api_list['_items']:
            for k, v in item.items():
                if self.args.name:
                    # looking by name
                    if k == 'description' and v == self.args.name:
                        # update_data = {"_id": item["_id"], "userEnabled": False}
                        item["userEnabled"] = enabled
                        self.api_update(item)
                if self.args.appkey:
                    if k == 'appKey' and v == self.args.appkey:
                        # update_data = {"_id": item["_id"], "userEnabled": False}
                        item["userEnabled"] = enabled
                        self.api_update(item)