import httpx
import asyncio
import time
import json
import os

class frog:
    def __init__(self, url = 'http://localhost:8000/'):
        self.url = url

    async def start_acquisition(self):
        acquisition_url = self.url + '/runner/start'
        async with httpx.AsyncClient() as client:
            response_acquisition = await client.put(acquisition_url)
            print(f'Start acquisition status code: {response_acquisition}')

    async def start_acquisition_runners(self):
        acquisition_url = self.url + 'start?subRunnerId=acquisition'
        async with httpx.AsyncClient() as client:
            response_acquisition = await client.put(acquisition_url)
            print(f'Start acquisition runners status code: {response_acquisition}')

    async def start_retrieve_runners(self):
        retrieve_url = self.url + 'start?subRunnerId=retrieve'
        async with httpx.AsyncClient() as client:
            response_retrieve = await client.put(retrieve_url)
            print(f'Start retrieve runners status code: {response_retrieve}')

    async def stop_acquisition_runners(self):
        acquisition_url = self.url + 'stop?subRunnerId=acquisition'
        async with httpx.AsyncClient() as client:
            response_acquisition = await client.put(acquisition_url)
            print(f'Stop acquisition runners status code: {response_acquisition}')

    async def stop_retrieve_runners(self):
        retrieve_url = self.url + 'stop?subRunnerId=retrieve'
        async with httpx.AsyncClient() as client:
            response_retrieve = await client.put(retrieve_url)
            print(f'Stop retrieve runners status code: {response_retrieve}')

    async def start_frog_runners(self):
        await self.start_acquisition_runners()
        await self.start_retrieve_runners()

    async def stop_frog_runners(self):
        await self.stop_acquisition_runners()
        await self.stop_retrieve_runners()

    async def get_acquisition_data(self):
        acquisition_url = self.url + 'runner/lastResult/json?subRunnerId=acquisition'
        async with httpx.AsyncClient() as client:
            acquisition_response = await client.get(acquisition_url)
            if acquisition_response.status_code == 200:
                return acquisition_response.json()

    async def get_retrieve_data(self):
        retrieve_url = self.url + 'runner/lastResult/json?subRunnerId=retrieve'
        #print(retrieve_url)
        async with httpx.AsyncClient() as client:
            retrieve_response = await client.get(retrieve_url)
            if retrieve_response.status_code == 200:
                return retrieve_response.json()

    async def get_frog_data(self):
        acquisition_data = self.get_acquisition_data()
        retrieve_data = self.get_retrieve_data()
        return acquisition_data, retrieve_data