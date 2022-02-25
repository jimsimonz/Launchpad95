from _Framework.SessionComponent import SessionComponent
from .ClipSlotMK2 import ClipSlotMK2
from _Framework.SceneComponent import SceneComponent
import Live

class TrackRoutingHandler():
	def __init__(self, session_component, track):
		self.session_component = session_component
		self._setup_track_routing_listener(track)
		
	def _track_routing_changed(self):
		self.session_component._track_routing_changed()

	def _track_sub_routing_changed(self):
		self.session_component._track_routing_changed()

	def _setup_track_routing_listener(self, track):
			try:
				track.remove_current_output_routing_listener(self._track_routing_changed)
				track.remove_current_output_sub_routing_listener(self._track_sub_routing_changed)
			except:
				 pass
			track.add_current_output_routing_listener(self._track_routing_changed)
			track.add_current_output_sub_routing_listener(self._track_sub_routing_changed)

class SpecialSessionComponent(SessionComponent):

	""" Special session subclass that handles ConfigurableButtons """

	def __init__(self, num_tracks, num_scenes, stop_clip_buttons, control_surface, main_selector):
		self._stop_clip_buttons = stop_clip_buttons
		self._control_surface = control_surface
		self._main_selector = main_selector
		self._osd = None
		self.track_routing_listeners = []
		if self._control_surface._mk2_rgb:
			#use custom clip colour coding : blink and pulse for trig and play 
			SceneComponent.clip_slot_component_type = ClipSlotMK2
		SessionComponent.__init__(self, num_tracks = num_tracks, num_scenes = num_scenes, enable_skinning = True, name='Session', is_root=True)

		if self._control_surface._lpx or self._control_surface._mk3_rgb or self._control_surface._mk2_rgb:
			from .ColorsMK2 import CLIP_COLOR_TABLE, RGB_COLOR_TABLE
			self.set_rgb_mode(CLIP_COLOR_TABLE, RGB_COLOR_TABLE)

	def link_with_track_offset(self, track_offset):
		assert (track_offset >= 0)
		if self._is_linked():
			self._unlink()
		self.set_offsets(track_offset, 0)
		self._link()

	def _update_stop_clips_led(self, index):
		if ((self.is_enabled()) and (self._stop_track_clip_buttons != None) and (index < len(self._stop_track_clip_buttons))):
			button = self._stop_track_clip_buttons[index]
			tracks_to_use = self.tracks_to_use()
			track_index = index + self.track_offset()
			if 0 <= track_index < len(tracks_to_use):
				track = tracks_to_use[track_index]
				if track.fired_slot_index == -2:
					button.send_value(self._stop_clip_triggered_value)
				elif track.playing_slot_index >= 0:
					button.send_value(self._stop_clip_value)
				else:
					button.turn_off()
			else:
				button.send_value(4)

	def set_osd(self, osd):
		self._osd = osd

	def _track_routing_changed(self):
	#	Live.Base.log("SpecialSessionComponent - routing changed")
		self._update_OSD()

	def _setup_track_routing_listeners(self):
		tracks = self.tracks_to_use()
		for i in range(len(tracks)):
			if i >= len(self.track_routing_listeners):
				self.track_routing_listeners.append(TrackRoutingHandler(self, tracks[i]))
			else:
				 self.track_routing_listeners[i]._setup_track_routing_listener(tracks[i])
	
	def _update_OSD(self):
		if self._osd != None:
			self._osd.mode = "Session"
			for i in range(self._num_tracks):
				self._osd.attribute_names[i] = " "
				self._osd.attributes[i] = " "

			tracks = self.tracks_to_use()
			idx = 0

			trackroutings = []
			trackroutings.append(len(tracks)*2)
			trackroutings.append(self._track_offset)


			for i in range(len(tracks)):
				if tracks[i].output_routing_type == "Master":
					trackroutings.append(126)
					trackroutings.append(2)
				elif tracks[i].output_routing_type == "Ext. Out":
					chleft = chright = 0
					if tracks[i].output_routing_channel.layout == Live.Track.RoutingChannelLayout.stereo:
						splitname = tracks[i].output_routing_channel.display_name.split('/') 
						try:
							if len(splitname) > 0:
								chleft = int(splitname[0])
							if len(splitname) > 1:
								chright = int(splitname[1])
						except:
							Live.Base.log("SpecialSessionComponent- routing invalid: " +  tracks[i].output_routing_channel.display_name) 
							chleft = 125
					else:
						chleft = int(tracks[i].output_routing_channel.display_name)
					trackroutings.append(chleft)
				
					if tracks[i].output_routing_channel.layout == Live.Track.RoutingChannelLayout.mono:
						trackroutings.append(1)
					elif tracks[i].output_routing_channel.layout == Live.Track.RoutingChannelLayout.stereo:
						trackroutings.append(2)
					else:
						trackroutings.append(0)
				else:
					trackroutings.append(127)
					trackroutings.append(1)

				if idx < self._num_tracks and len(tracks) > i + self._track_offset:
					track = tracks[i + self._track_offset]
					if track != None:
						string_array_as_bytes = self._control_surface._encode_string_to_midi(track.name)
						#Live.Base.log("SpecialSessionComponent- tracknames: " + str(track.name))  
						self._control_surface._send_midi((240, 0, 32, 41, 2, 24, 51) + (i, len(string_array_as_bytes)) + tuple(string_array_as_bytes) + (247,))
					else:
						self._osd.attribute_names[idx] = " "
						self._control_surface._send_midi((240, 0, 32, 41, 2, 24, 51) + (i, 1) + (0, 247,))
					self._osd.attributes[idx] = " "
				else:
					self._control_surface._send_midi((240, 0, 32, 41, 2, 24, 51) + (i, 1) + (0, 247,))
				idx += 1


			self._osd.info[0] = " "
			self._osd.info[1] = " "
			self._osd.update()
			#Track routing infos
			self._control_surface._send_midi((240, 0, 32, 41, 2, 24, 53) + tuple(trackroutings) + (247,))
			self._setup_track_routing_listeners()

	def unlink(self):
		if self._is_linked():
			self._unlink()

	def update(self):
		SessionComponent.update(self)
		if self._main_selector._main_mode_index == 0:
			self._update_OSD()

	def set_enabled(self, enabled):
		SessionComponent.set_enabled(self, enabled)
		if self._main_selector._main_mode_index == 0:
			self._update_OSD()

	def _reassign_tracks(self):
		SessionComponent._reassign_tracks(self)
		if self._main_selector._main_mode_index == 0:
			self._update_OSD()
