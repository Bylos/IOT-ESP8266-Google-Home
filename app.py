import websockets
import asyncio
import json
import time, os


class HttpWSSProtocol(websockets.WebSocketServerProtocol):
    rwebsocket = None
    rddata = None
    async def handler(self):
        try:
            #request_line, headers = await websockets.http.read_headers(self.reader)
            request_line = await websockets.http.read_line(self.reader)
            method, path, version = request_line[:-2].split(b' ', 2)
            headers =  await websockets.http.read_headers(self.reader)
            print('path: '+path+'length: '+str(len(self.reader._buffer)))
			#method, path, version = request_line[:-2].decode().split(None, 2)
            #websockets.accept()
        except Exception as e:
            print(e.args)
            self.writer.close()
            self.ws_server.unregister(self)

            raise

        # TODO: Check headers etc. to see if we are to upgrade to WS.
        if path == '/ws':
            # HACK: Put the read data back, to continue with normal WS handling.
            self.reader.feed_data(bytes(request_line))
            self.reader.feed_data(headers.as_bytes().replace(b'\n', b'\r\n'))

            return await super(HttpWSSProtocol, self).handler()
        else:
            try:
                return await self.http_handler(method, path, version)
            except Exception as e:
                print(e)
            finally:

                self.writer.close()
                self.ws_server.unregister(self)


    async def http_handler(self, method, path, version):
        response = ''
        try:
            googleRequest = self.reader._buffer.decode('utf-8')
            googleRequestJson = json.loads(googleRequest)
            #{"location": "living", "state": "on", "device": "lights"}
            if 'what' in googleRequestJson['result']['resolvedQuery']:
                ESPparameters = googleRequestJson['result']['parameters']
                ESPparameters['query'] = '?'
            else:
                ESPparameters = googleRequestJson['result']['parameters']
                ESPparameters['query'] = 'cmd'
            # send command to ESP over websocket
            if self.rwebsocket== None:
                print("Device is not connected!")
                response = '\r\n'.join([
                    'HTTP/1.1 200 OK',
                    'Content-Type: text/json',
                    '',
                    '{"speech": "bla bla bla", "displayText": "bla bla bla"}',
                ])
                self.writer.write(response.encode())
                return
            await self.rwebsocket.send(json.dumps(ESPparameters))

            #wait for response and send it back to API.ai as is
            self.rddata = await self.rwebsocket.recv()
            #{"speech": "It is working", "displayText": "It is working"}
            print(self.rddata)
            state = json.loads(self.rddata)['state']
            self.rddata = '{"speech": "cest '+state+'", "displayText": "cest '+state+'"}'

            response = '\r\n'.join([
                'HTTP/1.1 200 OK',
                'Content-Type: text/json',
                '',
                ''+self.rddata+'',
            ])
        except Exception as e:
            print(e)
        self.writer.write(response.encode())

def updateData(data):
    HttpWSSProtocol.rddata = data

async def ws_handler(websocket, path):
    game_name = 'g1'
    try:
        HttpWSSProtocol.rwebsocket = websocket
        await websocket.send(json.dumps({'event': 'OK'}))
        data ='{"empty":"empty"}'
        while True:
            data = await websocket.recv()
            updateData(data)
    except Exception as e:
        print(e)
    finally:
        print("")



port = int(os.getenv('PORT', 5687))
start_server = websockets.serve(ws_handler, '', port, klass=HttpWSSProtocol)
print('I am testing the output')
asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
