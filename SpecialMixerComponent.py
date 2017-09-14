import base64
from _Framework.MixerComponent import MixerComponent
from DefChannelStripComponent import DefChannelStripComponent
from _Framework.ButtonElement import ButtonElement


class SpecialMixerComponent(MixerComponent):

	""" Class encompassing several defaultable channel strips to form a mixer """

	def __init__(self, control_surface, num_tracks, num_returns = 0):
		self._osd = None
		MixerComponent.__init__(self, num_tracks, num_returns)
		self._unarm_all_button = None
		self._unsolo_all_button = None
		self._unmute_all_button = None
		self._control_surface = control_surface

	def disconnect(self):
		if self._unarm_all_button != None:
			self._unarm_all_button.remove_value_listener(self._unarm_all_value)
			self._unarm_all_button = None
		if self._unsolo_all_button != None:
			self._unsolo_all_button.remove_value_listener(self._unsolo_all_value)
			self._unsolo_all_button = None
		if self._unmute_all_button != None:
			self._unmute_all_button.remove_value_listener(self._unmute_all_value)
			self._unmute_all_button = None
		MixerComponent.disconnect(self)

	def set_global_buttons(self, unarm_all, unsolo_all, unmute_all):
		assert isinstance(unarm_all, (ButtonElement, type(None)))
		assert isinstance(unsolo_all, (ButtonElement, type(None)))
		assert isinstance(unmute_all, (ButtonElement, type(None)))
		if self._unarm_all_button != None:
			self._unarm_all_button.remove_value_listener(self._unarm_all_value)
		self._unarm_all_button = unarm_all
		if self._unarm_all_button != None:
			self._unarm_all_button.add_value_listener(self._unarm_all_value)
			self._unarm_all_button.turn_off()
		if self._unsolo_all_button != None:
			self._unsolo_all_button.remove_value_listener(self._unsolo_all_value)
		self._unsolo_all_button = unsolo_all
		if self._unsolo_all_button != None:
			self._unsolo_all_button.add_value_listener(self._unsolo_all_value)
			self._unsolo_all_button.turn_off()
		if self._unmute_all_button != None:
			self._unmute_all_button.remove_value_listener(self._unmute_all_value)
		self._unmute_all_button = unmute_all
		if self._unmute_all_button != None:
			self._unmute_all_button.add_value_listener(self._unmute_all_value)
			self._unmute_all_button.turn_off()

	def _reassign_tracks(self):
		MixerComponent._reassign_tracks(self)
		if self._is_enabled:
			self._update_OSD()

	def _create_strip(self):
		return DefChannelStripComponent()

	def set_osd(self, osd):
		self._osd = osd

	def update(self):
		MixerComponent.update(self)
		if self._is_enabled:
			self._update_OSD()

	def set_enabled(self, enabled):
		MixerComponent.set_enabled(self, enabled)
		if enabled:
			self._update_OSD()

	def _update_OSD(self):
		if self._osd != None:
			self._osd.mode = "Mixer"
			for i in range(8):
				self._osd.attribute_names[i] = " "
				self._osd.attributes[i] = " "

			tracks = self.tracks_to_use()
			idx = 0
			for i in range(len(tracks)):
				if idx < 8 and len(tracks) > i + self._track_offset:
					track = tracks[i + self._track_offset]
					if track != None:
						string_array_encoded = base64.b64encode(track.name.encode('UTF-16LE'))
						string_array_as_bytes =  [ord(c) for c in string_array_encoded]
						self._control_surface._send_midi((240, 0, 32, 41, 2, 24, 51) + (i, len(string_array_as_bytes)) + tuple(string_array_as_bytes) + (247,))
						#self._osd.attribute_names[idx] = str(track.name) removed as international characters make this throw
						self._osd.attribute_names[idx] = " "
					else:
						self._control_surface._send_midi((240, 0, 32, 41, 2, 24, 51) + (i, 1) + (0, 247,))
						self._osd.attribute_names[idx] = " "
				else:
					self._control_surface._send_midi((240, 0, 32, 41, 2, 24, 51) + (i, 1) + (0, 247,))
				idx += 1

			self._osd.info[0] = " "
			self._osd.info[1] = " "
			self._osd.update()

	def _unarm_all_value(self, value):
		assert (self._unarm_all_button != None)
		assert (value in range(128))
		if self.is_enabled():
			if value != 0 or not self._unarm_all_button.is_momentary():
				for track in self.song().tracks:
					if track.can_be_armed and track.arm:
						track.arm = False

	def _unsolo_all_value(self, value):
		assert (self._unsolo_all_button != None)
		assert (value in range(128))
		if self.is_enabled():
			if value != 0 or not self._unsolo_all_button.is_momentary():
				for track in tuple(self.song().tracks) + tuple(self.song().return_tracks):
					if track.solo:
						track.solo = False

	def _unmute_all_value(self, value):
		assert (self._unmute_all_button != None)
		assert (value in range(128))
		if self.is_enabled():
			if value != 0 or not self._unmute_all_button.is_momentary():
				for track in tuple(self.song().tracks) + tuple(self.song().return_tracks):
					if track.mute:
						track.mute = False
