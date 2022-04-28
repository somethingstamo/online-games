import time

import pygame
import shared_assets
from abc import ABC, abstractmethod
from typing import Union
import copy
from gui import Gui, GuiMouseEventHandler, get_auto_center_function, GuiKeyboardEventHandler
# from network import Network
# import assets
from utilities import Colors, Vert

pygame.init()
canvas = pygame.display.set_mode((600, 450), pygame.RESIZABLE)
pygame.display.set_caption("Online games and all that jazz.")
clock = pygame.time.Clock()
canvas_active = True

class Menus:
    class Menu(ABC):
        button_default_color = (210,) * 3
        button_mouse_holding_color = (150,) * 3
        button_mouse_over_color = (190,) * 3

        # Do I want to make TextInput be constantly darker while selected, instead of just when held?
        text_input_default_color = (255,) * 3
        text_input_mouse_holding_color = (230,) * 3
        text_input_mouse_over_color = (245,) * 3
        text_input_error_color = (255, 240, 240)

        def __init__(self):
            self.gui = Gui.ContainerElement(Vert(0, 0))

            def element_on_mouse_over(element):
                # TODO: Make a getter function for these, given a set of colors? And use it in ConnectedLobby?
                #  could it give back a dict with all four?
                if not any(element.mouse_buttons_holding):
                    element.col = self.text_input_mouse_over_color if isinstance(element, Gui.TextInput) \
                        else self.button_mouse_over_color

            def element_on_mouse_not_over(element):
                if not any(element.mouse_buttons_holding):
                    element.col = self.text_input_default_color if isinstance(element, Gui.TextInput) \
                        else self.button_default_color

            def element_on_mouse_down(element, *_):
                element.col = self.text_input_mouse_holding_color if isinstance(element, Gui.TextInput) \
                    else self.button_mouse_holding_color

            def element_on_mouse_up(element, *_):
                if element.mouse_is_over:
                    element.col = self.text_input_mouse_over_color if isinstance(element, Gui.TextInput) \
                        else self.button_mouse_over_color
                else:
                    element.col = self.text_input_default_color if isinstance(element, Gui.TextInput) \
                        else self.button_default_color

            self.element_mouse_functions = {
                "on_mouse_down": [element_on_mouse_down],
                "on_mouse_up": [element_on_mouse_up],
                "on_mouse_over": [element_on_mouse_over],
                "on_mouse_not_over": [element_on_mouse_not_over]
            }

        new_text_parameters = {
            "on_draw_before": [get_auto_center_function()]
            # get_auto_font_size_function(size_scaled_by_parent_height=0.75)]
        }

        @abstractmethod
        def resize_elements(self):
            ...

    class TitleScreenMenu(Menu):

        def __init__(self):
            super().__init__()

            def element_on_mouse_up(element, *_):
                global canvas_active

                if element is not mouse_event_handler.element_over:  # or Menus.menu_active is not self:
                    # Commented out code makes sure that if the user switches guis while holding the element, it will ignore that
                    # element's on_mouse_up. Unnecessary since checking if the mouse is over the element automatically handles this.
                    return

                if element is self.multiplayer_button:
                    username = self.username_text_field.text if self.username_text_field.text else default_username
                    if username:
                        Menus.set_active_menu(InitializedMenus.multiplayer_menu)
                    else:
                        self.username_text_field.col = self.text_input_error_color
                elif element is self.options_button:
                    Menus.set_active_menu(InitializedMenus.options_menu)
                elif element is self.exit_button:
                    canvas_active = False

            self.element_mouse_functions["on_mouse_up"].append(element_on_mouse_up)

            self.button_list = [Gui.TextInput(
                col=self.text_input_default_color, valid_chars=Gui.TextInput.USERNAME_CHARS,
                default_text="Username", max_text_length=18, horizontal_align="CENTER", **self.element_mouse_functions
            )]

            for title in ["Multiplayer", "Options", "Exit"]:
                self.button_list.append(
                    new_button := Gui.Rect(col=self.button_default_color, **self.element_mouse_functions))
                new_button.add_element(Gui.Text(title, **self.new_text_parameters))
            self.username_text_field, self.multiplayer_button, self.options_button, self.exit_button = \
                self.button_list

            self.game_title = Gui.Text("GAME :>")

            # TODO: I tried to make a child of create_lobby_button with drag_parent=create_lobby_button & it crashed

            self.gui.add_element(self.button_list + [self.game_title])

        def resize_elements(self):
            canvas_size = Vert(canvas.get_size())
            # element_scale = min(canvas_size.x / 600, canvas_size.y / 450)
            canvas_scale = canvas_size / Vert(600, 450)

            self.game_title.pos = canvas_size * Vert(0.5, (2.5 / 2) / 7)
            self.game_title.font_size = 75 * min(canvas_scale.x, canvas_scale.y)

            button_size = Vert(400, 50)
            # Multiplying canvas_scale.x means that it will not have an effect on the size until a certain width
            text_scale = min(1, canvas_scale.x * 1.8, canvas_scale.y)
            for i, button in enumerate(self.button_list):
                button.size = button_size * canvas_scale
                button.pos = canvas_size * Vert(0.5, (2.5 + i) / 7) - Vert(button.size.x / 2, 0)
                if button is not self.username_text_field:
                    button.contents[0].font_size = button_size.y * text_scale * 0.75

    class OptionsMenu(Menu):
        def __init__(self):
            super().__init__()

            def element_on_mouse_up(element, *_):
                if element is self.options_back_button:
                    Menus.set_active_menu(InitializedMenus.title_screen_menu)
            self.element_mouse_functions["on_mouse_up"].append(element_on_mouse_up)

            self.button_list = []
            for title in ["Keybinds", "Other Option", "Option 3", "Back"]:
                self.button_list.append(
                    new_button := Gui.Rect(col=self.button_default_color, **self.element_mouse_functions))
                new_button.add_element(Gui.Text(title, **self.new_text_parameters))
            self.options_keybinds_button, _, _, self.options_back_button = self.button_list

            self.gui.add_element(self.button_list)

        def resize_elements(self):
            canvas_size = Vert(canvas.get_size())
            canvas_scale = canvas_size / Vert(600, 450)

            text_scale = min(1, canvas_scale.x * 1.8, canvas_scale.y)
            button_size = Vert(400, 50)
            for i, button in enumerate(self.button_list):
                button.size = button_size * canvas_scale
                button.pos = canvas_size * Vert(0.5, 0.2 * (1 + i)) - button.size / 2
                button.contents[0].font_size = button_size.y * text_scale * 0.75

    class MultiplayerMenu(Menu):
        class ConnectedLobby:
            # Maybe make this a shared asset
            LOBBY_LIST_ELEMENT_DEFAULT_COLOR = (240,) * 3
            LOBBY_LIST_ELEMENT_MOUSE_OVER_COLOR = (230,) * 3
            LOBBY_LIST_ELEMENT_MOUSE_HOLDING_COLOR = (200,) * 3
            LOBBY_LIST_ELEMENT_SELECTED_COLOR = (220,) * 3

            def __init__(self, lobby_data: shared_assets.LobbyData, parent_menu):
                def on_mouse_over(element):
                    if self.parent_menu.selected_lobby is not self:
                        if not any(element.mouse_buttons_holding):
                            self.list_gui_element.col = self.LOBBY_LIST_ELEMENT_MOUSE_OVER_COLOR

                def on_mouse_not_over(element):
                    if self.parent_menu.selected_lobby is not self:
                        if not any(element.mouse_buttons_holding):
                            self.list_gui_element.col = self.LOBBY_LIST_ELEMENT_DEFAULT_COLOR

                def on_mouse_down(*_):
                    self.list_gui_element.col = self.LOBBY_LIST_ELEMENT_MOUSE_HOLDING_COLOR

                def on_mouse_up(element, *_):
                    if element.mouse_is_over:
                        self.parent_menu.selected_lobby = self
                    else:
                        element.col = self.LOBBY_LIST_ELEMENT_DEFAULT_COLOR

                self.list_gui_element = Gui.Rect(col=self.LOBBY_LIST_ELEMENT_DEFAULT_COLOR,
                                                 on_mouse_down=on_mouse_down,
                                                 on_mouse_up=on_mouse_up,
                                                 on_mouse_over=on_mouse_over,
                                                 on_mouse_not_over=on_mouse_not_over)
                before_draw_funcs = [get_auto_center_function(align=["LEFT", "CENTER"],
                                                              offset_scaled_by_parent_height=Vert(0.1, -1/6)),
                                     get_auto_center_function(align=["LEFT", "CENTER"],
                                                              offset_scaled_by_parent_height=Vert(0.1,  0.275)),
                                     get_auto_center_function(align=["RIGHT", "CENTER"],
                                                              offset_scaled_by_parent_height=Vert(-0.1, -1/6)),
                                     get_auto_center_function(align=["RIGHT", "CENTER"],
                                                              offset_scaled_by_parent_height=Vert(-0.1, 0.275))
                                     ]
                self.list_gui_element.add_element([
                    container := Gui.BoundingContainer(),
                    img := Gui.Rect(col=(200,) * 3, ignored_by_mouse=True)
                ])

                container.add_element([
                    title := Gui.Text(text_align=["LEFT", "CENTER"],
                                      on_draw_before=before_draw_funcs[0]),
                    game_title := Gui.Text(text_align=["LEFT", "CENTER"],
                                           on_draw_before=before_draw_funcs[1]),
                    count := Gui.Text(text_align=["RIGHT", "CENTER"],
                                      on_draw_before=before_draw_funcs[2]),
                    owner := Gui.Text(text_align=["RIGHT", "CENTER"],
                                      on_draw_before=before_draw_funcs[3])
                ])

                self.parent_menu = parent_menu

                self.text_container, self.game_image = container, img
                self.title_element, self.game_title_element, self.owner_element, self.player_count_element = \
                    title, game_title, owner, count
                self.info_gui_element = Gui.BoundingContainer()

                self._lobby_data: shared_assets.LobbyData = shared_assets.LobbyData(lobby_data.lobby_id)
                self.lobby_data = lobby_data

            def set_selected(self, selected: bool):
                if selected:
                    self.list_gui_element.col = self.LOBBY_LIST_ELEMENT_SELECTED_COLOR
                else:
                    self.list_gui_element.col = self.LOBBY_LIST_ELEMENT_DEFAULT_COLOR

            @property
            def lobby_data(self):
                return copy.copy(self._lobby_data)

            @lobby_data.setter
            def lobby_data(self, value):
                if value.lobby_id != self.lobby_id and self.lobby_id is not None:
                    raise ValueError("Tried to set lobby to another without a matching ID")
                self.lobby_title = value.lobby_title
                self.owner = value.owner
                self.game_title = value.game_title
                self.players = value.players
                self.max_players = value.max_players

            @property
            def lobby_title(self):
                return self._lobby_data.lobby_title

            @lobby_title.setter
            def lobby_title(self, value):
                if value == self._lobby_data.lobby_title:
                    return
                self._lobby_data.lobby_title = value
                self.title_element.text = value

            @property
            def owner(self):
                return self._lobby_data.owner

            @owner.setter
            def owner(self, value):
                if value == self._lobby_data.owner:
                    return
                self._lobby_data.owner = value
                self.owner_element.text = value

            @property
            def game_title(self):
                return self._lobby_data.game_title

            @game_title.setter
            def game_title(self, value):
                if value == self._lobby_data.game_title:
                    return
                self._lobby_data.game_title = value
                self.game_title_element.text = value

            @property
            def player_count(self):
                return len(self._lobby_data.players)

            @player_count.setter
            def player_count(self, value):
                self.player_count_element.text = f"{value}/{self.max_players}" if self.max_players is not None else \
                    f"{value}"

            @property
            def players(self):
                return self._lobby_data.players

            @players.setter
            def players(self, value):
                if value == self._lobby_data.players:
                    return
                self._lobby_data.players = value
        #         TODO: Set players element here.
                self.player_count = len(value)

            @property
            def max_players(self):
                return self._lobby_data.max_players

            @max_players.setter
            def max_players(self, value):
                if value == self._lobby_data.max_players:
                    return
                self._lobby_data.max_players = value
                self.player_count_element.text = f"{self.player_count}/{value}" \
                    if self.max_players is not None else f"{self.player_count}"

            @property
            def lobby_id(self):
                return self._lobby_data.lobby_id

        def __init__(self):
            super().__init__()

            # region Gui Initialization
            def element_on_mouse_up(element, *_):
                if element is self.back_button:
                    self.selected_lobby = None
                    Menus.set_active_menu(InitializedMenus.title_screen_menu)

            self.element_mouse_functions["on_mouse_up"].append(element_on_mouse_up)

            self.lobby_list_background = Gui.Rect(col=(255,) * 3)

            self.back_button = Gui.Rect(col=self.button_default_color, **self.element_mouse_functions)
            self.back_button.add_element(Gui.Text("Back", **self.new_text_parameters))

            self.lobby_info = Gui.Rect(col=(245,) * 3)

            self.button_list = []
            for title in ["Join Lobby", "Refresh", "Create Lobby"]:
                self.button_list.append(new_button := Gui.Rect(col=self.button_default_color, **self.element_mouse_functions))
                new_button.add_element(Gui.Text(title, **self.new_text_parameters))

            self.gui.add_element([self.lobby_list_background, self.back_button, self.lobby_info] + self.button_list)
            # endregion

            # region Lobby info contents initialization
            self.game_image = Gui.Rect(col=(220,) * 3)

            # A thin wrapper just inside lobby_info that lets the user easily disable the contents of lobby_info
            self.lobby_info_inside_wrapper = Gui.ContainerElement(active=False)

            self.player_list_container = Gui.BoundingContainer()
            self.player_list_visual_container = Gui.Rect()
            self.player_list_title = Gui.Text()
            self.player_list: list[list[Gui.Text], list[Gui.Text]] = [[], []]

            self.game_info_container = Gui.BoundingContainer()
            before_draw_funcs = [
                get_auto_center_function(align=["LEFT", "CENTER"], offset_scaled_by_parent_height=Vert(0.05, -0.25)),
                get_auto_center_function(align=["LEFT", "CENTER"], offset_scaled_by_parent_height=Vert(0.05, 0.08)),
                get_auto_center_function(align=["LEFT", "CENTER"], offset_scaled_by_parent_height=Vert(0.05, 0.33))
            ]
            self.game_info_container.add_element([
                title := Gui.Text(text_align=["LEFT", "CENTER"],
                                  on_draw_before=before_draw_funcs[0]),
                game_title := Gui.Text(text_align=["LEFT", "CENTER"],
                                       on_draw_before=before_draw_funcs[1]),
                owner := Gui.Text(text_align=["LEFT", "CENTER"],
                                  on_draw_before=before_draw_funcs[2])
            ])

            self.lobby_title, self.game_title, self.owner = title, game_title, owner

            self.lobby_info_inside_wrapper.add_element([
                self.game_image,
                self.player_list_visual_container,
                self.player_list_container,
                self.game_info_container,
                self.player_list_title
            ])
            self.lobby_info.add_element(self.lobby_info_inside_wrapper)
            # endregion

            self.connected_lobbies: list[Menus.MultiplayerMenu.ConnectedLobby] = []
            self._selected_lobby: Union[Menus.MultiplayerMenu.ConnectedLobby, None] = None

        def set_lobby_info(self, lobby: ConnectedLobby):
            self.lobby_title.text = lobby.lobby_title
            self.owner.text = f"Owner: {lobby.owner}"
            self.game_title.text = f"Game: {lobby.game_title}"
            self.player_list_title.text = f"Players: " + (f"{lobby.player_count}/{lobby.max_players}" if
                                                          lobby.max_players is not None else f"{lobby.player_count}")

            self.player_list = [[], []]
            for i, username in enumerate(lobby.players):
                self.player_list[i % 2].append((Gui.Text(username, text_align=["LEFT", "CENTER"]),
                                                Gui.Circle(no_fill=True)))
            self.player_list_container.contents = sum(self.player_list[0] + self.player_list[1], start=())

            self.resize_lobby_info_elements()

        @property
        def selected_lobby(self):
            return self._selected_lobby

        @selected_lobby.setter
        def selected_lobby(self, value):
            if self._selected_lobby:
                self._selected_lobby.set_selected(False)

            self._selected_lobby = value

            if self._selected_lobby:
                self.lobby_info_inside_wrapper.active = True
                self.set_lobby_info(self._selected_lobby)
                self._selected_lobby.set_selected(True)
            else:
                self.lobby_info_inside_wrapper.active = False

        def set_lobbies(self, lobbies: list[shared_assets.LobbyData]):
            connected_lobbies_by_id = {lobby.lobby_id: lobby for lobby in self.connected_lobbies}
            incoming_lobbies_by_id = {lobby.lobby_id: lobby for lobby in lobbies}

            if set(connected_lobbies_by_id) != set(incoming_lobbies_by_id):

                for i, lobby in enumerate(self.connected_lobbies):
                    if lobby.lobby_id not in incoming_lobbies_by_id:
                        self.lobby_list_background.remove_element(lobby.list_gui_element)
                        self.resize_lobby_list_elements()

                        if lobby is self.selected_lobby:
                            self.selected_lobby = None
                        del self.connected_lobbies[i]

                for i, lobby in enumerate(lobbies):
                    if lobby.lobby_id not in connected_lobbies_by_id:
                        self.connected_lobbies.append(new_lobby := Menus.MultiplayerMenu.ConnectedLobby(lobby, self))
                        self.lobby_list_background.add_element(new_lobby.list_gui_element)

            for lobby_id, lobby in incoming_lobbies_by_id.items():
                if lobby_id in connected_lobbies_by_id:
                    corresponding_lobby = connected_lobbies_by_id[lobby_id]
                    corresponding_lobby.lobby_data = lobby

            if self._selected_lobby:
                self.set_lobby_info(self._selected_lobby)

            self.resize_lobby_list_elements()

        def resize_lobby_list_elements(self):
            if len(self.connected_lobbies) == 0:
                return
            element_height = min(self.lobby_list_background.size.y / len(self.connected_lobbies),
                                 self.lobby_list_background.size.x * 0.2)
            for i, lobby in enumerate(self.connected_lobbies):
                lobby.list_gui_element.pos = Vert(0, i * element_height)
                tall_element_height = element_height + (2 if i != len(self.connected_lobbies) - 1 else 1)
                # Use tall_element_height so that there is no accidental space between elements
                lobby.list_gui_element.size = Vert(self.lobby_list_background.size.x, tall_element_height)

                lobby.game_image.size = Vert(element_height, tall_element_height)

                lobby.text_container.size = lobby.list_gui_element.size - Vert(lobby.game_image.size.x, 0)
                lobby.text_container.pos = Vert(lobby.game_image.size.x, 0)

                # font_size * size_per_font_size = element width/2 => font_size = element_width/2 / size_per_font_size

                lobby.title_element.font_size = \
                    min(lobby.text_container.size.x * 0.75 / lobby.title_element.size_per_font_size.x,
                        lobby.text_container.size.y * 0.5 / lobby.title_element.size_per_font_size.y)
                lobby.game_title_element.font_size = \
                    min(lobby.text_container.size.x * 0.45 / lobby.game_title_element.size_per_font_size.x,
                        lobby.text_container.size.y * 0.3 / lobby.game_title_element.size_per_font_size.y)
                lobby.owner_element.font_size = \
                    min(lobby.text_container.size.x * 0.45 / lobby.owner_element.size_per_font_size.x,
                        lobby.text_container.size.y * 0.3 / lobby.owner_element.size_per_font_size.y)
                lobby.player_count_element.font_size = \
                    min(lobby.text_container.size.x * 0.2 / lobby.player_count_element.size_per_font_size.x,
                        lobby.text_container.size.y * 0.45 / lobby.player_count_element.size_per_font_size.y)

        def resize_lobby_info_elements(self):
            self.game_image.size = Vert(1, 1) * min(self.lobby_info.size.x / 2, self.lobby_info.size.y / 2)

            self.game_info_container.size = Vert(self.lobby_info.size.x - self.game_image.size.x,
                                                 self.game_image.size.y)
            self.game_info_container.pos = Vert(self.game_image.size.x, 0)

            if self.player_list_title.text:
                self.player_list_title.font_size = min(self.lobby_info.size.y / 10, self.lobby_info.size.x / 8)

            self.player_list_visual_container.pos = Vert(0, self.game_image.size.y - 2)
            self.player_list_visual_container.size = Vert(self.lobby_info.size.x,
                                                          self.lobby_info.size.y - self.player_list_visual_container.pos.y + 1)

            self.player_list_container.pos = Vert(0, self.game_image.size.y + self.player_list_title.font_size * 1.2)
            self.player_list_container.size = Vert(self.lobby_info.size.x,
                                                   self.lobby_info.size.y - self.player_list_container.pos.y)
            self.player_list_title.pos = Vert(self.lobby_info.size.x / 2,
                                              (self.player_list_visual_container.pos.y + self.player_list_container.pos.y) / 2)

            if self.lobby_title.text:
                self.lobby_title.font_size = min(self.game_info_container.size.y / 2.5,
                                                 self.game_info_container.size.x / self.lobby_title.size_per_font_size.x * 0.9)
            if self.game_title.text:
                self.game_title.font_size = min(self.game_info_container.size.y / 4,
                                                self.game_info_container.size.x / self.game_title.size_per_font_size.x * 0.9)
            if self.owner.text:
                self.owner.font_size = min(self.game_info_container.size.y / 4,
                                           self.game_info_container.size.x / self.owner.size_per_font_size.x * 0.9)

            height = len(self.player_list[0])
            vertical_padding = self.player_list_container.size.y / 20
            left_padding = self.player_list_container.size.x / 12
            spacing = (self.player_list_container.size.y - vertical_padding * 2) / max(height, 3)
            max_font_size = spacing
            for column_num in [0, 1]:
                for i, element in enumerate(self.player_list[column_num]):
                    text, circle = element
                    font_size = min(max_font_size,
                                    (self.player_list_container.size.x * 0.45 - left_padding) / text.size_per_font_size.x)
                    text.font_size = font_size
                    text.pos = Vert(left_padding + column_num * self.player_list_container.size.x / 2,
                                    (0.5 + i) * spacing + vertical_padding)

                    circle.pos = text.pos - Vert(left_padding / 2, 0)
                    circle.rad = min(max_font_size * 0.2, left_padding / 3)

        def resize_elements(self):
            canvas_size = Vert(canvas.get_size())

            canvas_scale = canvas_size / Vert(600, 450)

            padding = Vert(1, 1) * min(canvas_size.x, canvas_size.y) / 30

            self.lobby_info.pos = Vert(canvas_size.x / 2 + padding.x / 2,
                                       padding.y)
            self.lobby_info.size = Vert(canvas_size.x / 2 - padding.x * 1.5,
                                        canvas_size.y / 2 - padding.y)

            base_button_height = 55
            button_size = Vert(canvas_size.x / 2 - padding.x * 1.5, base_button_height) * Vert(1, canvas_scale.y)

            button_list_pos = self.lobby_info.pos + Vert(0, self.lobby_info.size.y + padding.y)
            button_list_size = Vert(self.lobby_info.size.x, canvas_size.y - button_list_pos.y - padding.y)
            button_list_padding = (button_list_size.y - 3 * button_size.y) / 2

            text_scale = min(1, canvas_scale.x, canvas_scale.y)
            for i, button in enumerate(self.button_list + [self.back_button]):
                button.size = button_size
                button.contents[0].font_size = base_button_height * text_scale * 0.75

                if button is self.back_button:
                    button.pos = padding
                else:
                    button.pos = button_list_pos + Vert(0, i * (button.size.y + button_list_padding))

            self.lobby_list_background.pos = Vert(padding.x,
                                                   self.back_button.pos.y + self.back_button.size.y + padding.y)
            self.lobby_list_background.size = Vert(canvas_size.x / 2 - padding.x * 1.5,
                                                    canvas_size.y - self.lobby_list_background.pos.y - padding.y)

            self.resize_lobby_list_elements()
            self.resize_lobby_info_elements()

    @classmethod
    def set_active_menu(cls, value):
        cls.menu_active = value
        cls.menu_active.resize_elements()

    menu_active: Union[Menu, None] = None

class InitializedMenus:
    title_screen_menu = Menus.TitleScreenMenu()
    options_menu = Menus.OptionsMenu()
    multiplayer_menu = Menus.MultiplayerMenu()

    Menus.set_active_menu(multiplayer_menu)


default_username = ""
keyboard_event_handler = GuiKeyboardEventHandler()
mouse_event_handler = GuiMouseEventHandler(keyboard_event_handler)

InitializedMenus.multiplayer_menu.set_lobbies([
    shared_assets.LobbyData(1, "Cool Lobby", "UsernameHere", ["hi", "hi2, hi3"], "Snake", None),
    shared_assets.LobbyData(3, "LOOOONG LOBBYY NAMMEEE 3", "WWWWWWWWWWWWWWWWWW", ["hi", "hi2"], "LOOONG NAMEEEEEE", 5),
    shared_assets.LobbyData(2, "Lob", "Name", ["username1", "username2", "username3"], "Short", 6)
])
a, b = time.perf_counter(), True

def on_frame():
    canvas.fill(Colors.light_gray)

    if Menus.menu_active:
        Menus.menu_active.gui.draw(canvas)

    global b
    if time.perf_counter() - a > 2 and b:
        b = False
        InitializedMenus.multiplayer_menu.set_lobbies([
            shared_assets.LobbyData(1, "Cool Lobby", "UsernameHere", ["hi", "hi2", "hi3"], "Snake", 2),
            shared_assets.LobbyData(5, "Lobby 3", "username", ["InsertUniqueName", "hi2"], "bruh", 7),
            shared_assets.LobbyData(2, "Lob (but the name's longer)", "Name",
                                    ["Username1", "Username2", "username3", "username4", "username5", "username6", "username7"], "Short", 8)
        ])

    mouse_event_handler.main(Menus.menu_active.gui)
    keyboard_event_handler.main(Menus.menu_active.gui)

def main():
    global canvas_active
    while canvas_active:
        for event in pygame.event.get():
            keyboard_event_handler.handle_pygame_keyboard_event(event)
            if event.type == pygame.QUIT:
                # TODO: Disconnect from lobby when this runs
                canvas_active = False
            elif event.type == pygame.WINDOWRESIZED:
                Menus.menu_active.resize_elements()

        on_frame()

        clock.tick(60)
        pygame.display.flip()


if __name__ == "__main__":
    # network = Network()
    main()
