from __future__ import annotations
import socket
import _thread
import pickle
from typing import Sequence
import shared_assets
from shared_assets import GameAssets, Messages, port, max_chat_messages, Client
from server_assets import GameServer, game_servers_by_id

_ = shared_assets

# TODO: Handle errors so the server doesn't die out of nowhere

lobbies: dict[int, Lobby] = {}

class Lobby:
    available_lobby_id = 0

    def __init__(self, host: ConnectedClient, settings: GameAssets.Settings, title: str = "", private: bool = False):
        self.lobby_id = Lobby.available_lobby_id
        Lobby.available_lobby_id += 1

        self.title: str = title

        self._host_client: ConnectedClient = host
        self.player_clients: list[ConnectedClient] = [host]

        self.game_selected_id = None
        self.game_settings = settings
        self.max_players = 10
        self.chat_messages: list[str] = []

        self.private = private
        # self.password = None

        self.clients_with_game_initialized: int = 0
        self.current_game: GameServer | None = None

    @property
    def host_client(self):
        return self._host_client

    @host_client.setter
    def host_client(self, value: ConnectedClient):
        self._host_client = value
        if self.current_game:
            self.current_game.host_client = value

    def remove_player(self, player: ConnectedClient):
        for i, client_in_lobby in enumerate(self.player_clients):
            if client_in_lobby.client_id == player.client_id:
                client_in_lobby.lobby_in = None
                del self.player_clients[i]
                break

        if len(self.player_clients) == 0:
            delete_lobby(self, player)
            return

        if player.client_id is self._host_client.client_id:
            self.host_client = self.player_clients[0]

        if self.current_game:
            self.current_game.on_client_disconnect_private(player)

        self.send_lobby_info_to_members()
        send_lobbies_to_each_client(player)

    def get_lobby_info(self, include_in_lobby_info=True, include_chat=False):
        parameters = {
            "lobby_id": self.lobby_id,
            "lobby_title": self.title,
            "host": (self._host_client.username, self._host_client.client_id),
            "players": [(client.username, client.client_id) for client in self.player_clients],
            "game_id": self.game_selected_id,
            "max_players": self.max_players
        }
        if include_in_lobby_info:
            parameters["private"] = self.private
            parameters["game_settings"] = self.game_settings
        if include_chat:
            parameters["chat"] = self.chat_messages

        return Messages.LobbyInfo(**parameters)

    def send_lobby_info_to_members(self,
                                   players_to_ignore: ConnectedClient | Sequence[ConnectedClient] = None,
                                   include_chat: bool = False):
        if not isinstance(players_to_ignore, Sequence):
            players_to_ignore = [players_to_ignore]
        for member in self.player_clients:
            if member in players_to_ignore:
                continue
            server.send(member, Messages.LobbyInfoMessage(self.get_lobby_info(True, include_chat)))

    def start_game(self):
        def on_game_end():
            self.current_game = None
            send_lobbies_to_each_client()

        self.current_game = game_servers_by_id[self.game_selected_id](server,
                                                                      self.game_settings,
                                                                      self.player_clients,
                                                                      self._host_client,
                                                                      on_game_end)

        _thread.start_new_thread(self.current_game.on_game_start, ())
        _thread.start_new_thread(self.current_game.call_on_frame, ())
        send_lobbies_to_each_client()

class ConnectedClient(Client):
    """A class representing a client that is connected to the server, including all information necessary for server to communicate with said client."""

    def __init__(self, client_id, conn, address, username=None):
        super().__init__(username, client_id)
        self.client_id: int = client_id
        self.conn = conn
        self.address = address
        self.username = username

        self.lobby_in: Lobby | None = None

class Server:
    # Should the client join the server when they start the game, or when they join the lobby?
    DEFAULT_PORT = port

    def __init__(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        port_to_try = self.DEFAULT_PORT
        while True:
            try:
                self.socket.bind(("", port_to_try))
                break
            except socket.error as e:
                print("Unable to bind socket: ", e)
                port_to_try = int(input("Input new port: "))

        self.socket.listen()
        print("Server started, waiting for client(s) to connect")

    @staticmethod
    def send(client, message: Messages.Message):
        try:
            outgoing_message = pickle.dumps(message)
        except Exception as err:
            print(f"Error: Error when attempting to pickle {message.name}: {repr(err)}")
            return

        try:
            client.conn.sendall(outgoing_message)
        except ConnectionResetError:
            print(f"Error: Attempted to send message of type {message.name} to closed client at address {client.address}. This is likely not an issue.")
            return
        except Exception as err:
            print(f"Error: Error when attempting to send {message.name} to client at address {client.address}: {repr(err)}")
            return

        print(f"  [S] Sent message of type {message.name} to address {client.address}")
        # TODO: I'm catching all errors, but what if I dont want to?

    @staticmethod
    def recv(client):
        try:
            incoming_message = client.conn.recv(4096)
        except (ConnectionAbortedError, ConnectionResetError) as err:
            print(f"Could not find client at address {client.address} ({repr(err)}). Assuming client is disconnected.")
            return Messages.DisconnectMessage()
        except Exception as err:
            print(f"Error: Error when attempting to receive message from client at address {client.address}: {repr(err)}")
            return Messages.ErrorMessage(err)

        try:
            message = pickle.loads(incoming_message)
        except Exception as err:
            print(f"Error: Unable to unpickle message from client at address {client.address}: {repr(err)}")
            return Messages.ErrorMessage(err)

        print(f"  [R] Received message of type {message.name} from address {client.address}")
        return message


clients_connected: dict[int, ConnectedClient] = {}

def delete_lobby(lobby: Lobby, player_to_ignore: ConnectedClient = None):
    for client in lobby.player_clients:
        server.send(client, Messages.KickedFromLobbyMessage())
        client.lobby_in = None

    del lobbies[lobby.lobby_id]

    send_lobbies_to_each_client(lobby.player_clients + [player_to_ignore] if player_to_ignore else [])

def send_lobbies_to_each_client(players_to_ignore: ConnectedClient | Sequence[ConnectedClient] = None):
    ids_to_ignore: list[int] = []
    if isinstance(players_to_ignore, ConnectedClient):
        ids_to_ignore = [players_to_ignore.client_id]
    elif isinstance(players_to_ignore, Sequence):
        ids_to_ignore = [player_to_ignore.client_id for player_to_ignore in players_to_ignore]

    lobbies_to_send = [lobby.get_lobby_info(False) for lobby in lobbies.values()
                       if not lobby.private and not lobby.current_game]
    for client in clients_connected.values():
        if client.lobby_in is None and client.client_id not in ids_to_ignore:
            server.send(client, Messages.LobbyListMessage(lobbies_to_send))

def listen_to_client(client: ConnectedClient):
    while True:
        message = server.recv(client)

        if message.name == Messages.GameDataMessage.name:
            if client.lobby_in.current_game:
                client.lobby_in.current_game.on_data_received(client, message.data)

        elif message.name == Messages.LobbyListRequest.name:
            server.send(client, Messages.LobbyListMessage([lobby.get_lobby_info(False) for lobby in lobbies.values()]))

        elif message.name == Messages.CreateLobbyMessage.name:
            client.username = message.username
            new_lobby = Lobby(client, message.settings, message.lobby_title, message.private)
            lobbies[new_lobby.lobby_id] = client.lobby_in = new_lobby
            send_lobbies_to_each_client()

        elif message.name == Messages.JoinLobbyMessage.name:
            if message.lobby_id not in lobbies:
                server.send(client, Messages.KickedFromLobbyMessage("Lobby no longer exists."))

            client.lobby_in = lobby = lobbies[message.lobby_id]
            client.username = message.username
            lobby.player_clients.append(client)
            send_lobbies_to_each_client()
            lobby.send_lobby_info_to_members(include_chat=True)

        elif message.name == Messages.DisconnectMessage.name:
            break

        elif message.name == Messages.LeaveLobbyMessage.name:
            client.lobby_in.remove_player(client)

        elif message.name == Messages.ChangeLobbySettingsMessage.name:
            old_host = client.lobby_in.host_client

            if message.lobby_title != message.unchanged:
                client.lobby_in.title = message.lobby_title

            if message.private != message.unchanged:
                client.lobby_in.private = message.private

            if message.host_id != message.unchanged:
                client.lobby_in.host_client = clients_connected[message.host_id]

            if message.game_settings != message.unchanged:
                client.lobby_in.game_settings = message.game_settings

            if message.game_id != message.unchanged:
                client.lobby_in.game_selected_id = message.game_id

            if {message.lobby_title, message.private, message.host_id, message.game_id} != {message.unchanged}:
                client.lobby_in.send_lobby_info_to_members(old_host)
                send_lobbies_to_each_client()
            elif message.game_settings != message.unchanged:
                # If the game settings were the only thing changed, we only need to send the lobbies to each client
                # (that is out of the lobby) if the max players changed. Otherwise, it would be useless.
                client.lobby_in.send_lobby_info_to_members(old_host)
                if "max_players" in message.game_settings.settings and message.game_settings.settings["max_players"] != client.lobby_in.max_players:
                    client.lobby_in.max_players = message.game_settings.settings["max_players"]
                    send_lobbies_to_each_client()

        elif message.name == Messages.KickPlayerFromLobbyMessage.name:
            kicked_player = clients_connected[message.client_id]
            kicked_player.lobby_in.remove_player(kicked_player)
            server.send(kicked_player, Messages.KickedFromLobbyMessage())

        elif message.name == Messages.NewChatMessage.name:
            CHAT_FORMAT = "<{}> {}"
            chat_message = CHAT_FORMAT.format(client.username, message.message)

            client.lobby_in.chat_messages.append(chat_message)

            if len(client.lobby_in.chat_messages) > max_chat_messages:
                client.lobby_in.chat_messages = \
                    client.lobby_in.chat_messages[len(client.lobby_in.chat_messages) - max_chat_messages:]

            for member in client.lobby_in.player_clients:
                server.send(member, Messages.NewChatMessage(chat_message))

        elif message.name == Messages.StartGameStartTimerMessage.name:
            for client_in_lobby in client.lobby_in.player_clients:
                if client_in_lobby.client_id != client.client_id:
                    server.send(client_in_lobby, Messages.StartGameStartTimerMessage(message.start_time))

        elif message.name == Messages.StartGameMessage.name:
            for client_in_lobby in client.lobby_in.player_clients:
                clients = [Client(connected_client.username, connected_client.client_id)
                           for connected_client in client.lobby_in.player_clients]
                host_client = Client(client.lobby_in.host_client.username, client.lobby_in.host_client.client_id)

                server.send(client_in_lobby, Messages.GameStartedMessage(clients,
                                                                         host_client,
                                                                         client.lobby_in.game_selected_id))
            client.lobby_in.clients_with_game_initialized = 0

        elif message.name == Messages.GameInitializedMessage.name:
            # Once each player's game class has been initialized, they will send this message. Makes sure that the
            # game server doesn't start running unless it knows all game clients are running and can accept messages.
            client.lobby_in.clients_with_game_initialized += 1
            # There's a tiny chance for error if somebody leaves the lobby/crashes before sending in a GameInitializedMessage, but the chance of that happening is miniscule (I hope).
            # Unless they crash when initializing the game (due to some glitch in the game initialization) (I'm just going to hope that doesn't happen)
            if client.lobby_in.clients_with_game_initialized >= len(client.lobby_in.player_clients):
                client.lobby_in.start_game()

    print(f"Disconnected from {client.address}")

    del clients_connected[client.client_id]

    if client.lobby_in is not None:
        client.lobby_in.remove_player(client)

def console_commands():
    while True:
        inp = input("")
        if inp in ["k", "kill"]:
            break

def listen_for_clients():
    while True:
        conn, address = server.socket.accept()

        print(f"Connected to {address}")

        client_id = 0
        while client_id in clients_connected:
            client_id += 1
        clients_connected[client_id] = client = ConnectedClient(client_id, conn, address)

        server.send(client, Messages.ConnectedMessage(address, client_id))

        _thread.start_new_thread(listen_to_client, (client,))


if __name__ == "__main__":
    server = Server()
    _thread.start_new_thread(listen_for_clients, ())
    console_commands()
