from __future__ import annotations
from typing import TYPE_CHECKING, Type, Callable
import shared_assets
import time

if TYPE_CHECKING:
    from server import Server, ConnectedClient

class GameServer:
    asset_class = shared_assets.GameAssets
    FPS: int | None = None
    """Amount of times per second this game server's on_frame() should be called. Leave 0 or None for never."""

    # region Private functions not to override
    def call_on_frame(self):
        while self.seconds_per_frame and self.game_running:
            current_time = time.time()
            if current_time - self.time_of_last_frame >= 1 / self.FPS:
                self.on_frame()
                self.time_of_last_frame = current_time

            time.sleep(self.seconds_per_frame / 5)

    def on_client_disconnect_private(self, client: ConnectedClient):
        host_left = client.client_id == self.host_client.client_id
        self.clients = list(filter(lambda c: c.client_id != client.client_id, self.clients))
        if host_left:
            self.host_client = self.clients[0]
        self.on_client_disconnect(client)
    # endregion

    # region Utility functions to call but not override
    def send_data(self, client: ConnectedClient | list[ConnectedClient], data):
        self.server.send(client, shared_assets.Messages.GameDataMessage(data))

    def send_data_to_all(self, data):
        for client in self.clients:
            self.send_data(client, data)

    def end_game(self):
        self.game_running = False
        self._on_game_over()
        for client in self.clients:
            self.server.send(client, shared_assets.Messages.GameOverMessage())

    @property
    def host_client(self):
        return self._host_client

    @host_client.setter
    def host_client(self, value):
        old_host = self._host_client
        self._host_client = value
        self.on_host_transfer(old_host)
    # endregion

    # region Automatically called functions to override

    # Call to super.__init__(*args) required for __init__!
    def __init__(self,
                 server: Server,
                 settings: shared_assets.GameAssets.Settings,
                 clients: list[ConnectedClient],
                 host_client: ConnectedClient,
                 on_game_over: Callable):
        self.server: Server = server
        self.settings = settings
        self.clients: list[ConnectedClient] = clients
        self._host_client: ConnectedClient = host_client

        self.game_running = True
        self._on_game_over = on_game_over

        self.time_of_last_frame = 0
        self.seconds_per_frame = 1 / self.FPS if self.FPS else None

        self.start_time = time.time()

    def on_game_start(self):
        ...

    def on_data_received(self, client_from: ConnectedClient, data):
        ...

    def on_frame(self):
        ...

    def on_client_disconnect(self, client):
        ...

    def on_host_transfer(self, old_host: ConnectedClient):
        print(f"host has been transferred from {old_host.username} to {self.host_client.username}")
    # endregion

class SnakeServer(GameServer):
    asset_class = shared_assets.SnakeAssets

class PongServer(GameServer):
    asset_class = shared_assets.PongAssets

    def on_game_start(self):
        for i, client in enumerate(self.clients):
            horizontal_dir = i * 2 - 1
            self.send_data(client, self.asset_class.Messages.BallHit(None, (horizontal_dir * 6, 6)))

    def on_data_received(self, client_from: ConnectedClient, data):
        if isinstance(data, self.asset_class.Messages.BallHit):
            print("got data")
        if isinstance(data, (self.asset_class.Messages.BallHit, self.asset_class.Messages.PaddleMove)):
            for client in self.clients:
                if client.client_id != client_from.client_id:
                    self.send_data(client, data)


game_servers: list[Type[GameServer]] = [GameServer, SnakeServer, PongServer]
game_servers_by_id: dict[str, Type[GameServer]] = {game.asset_class.game_id: game for game in game_servers}
