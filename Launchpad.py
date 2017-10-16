from __future__ import with_statement
import Live
from _Framework.ControlSurface import ControlSurface
from _Framework.InputControlElement import MIDI_CC_TYPE, MIDI_NOTE_TYPE
from _Framework.ButtonElement import ButtonElement
from _Framework.ButtonMatrixElement import ButtonMatrixElement
from ConfigurableButtonElement import ConfigurableButtonElement
from MainSelectorComponent import MainSelectorComponent
from NoteRepeatComponent import NoteRepeatComponent
from M4LInterface import M4LInterface
import Settings

DO_COMBINE = Live.Application.combine_apcs()  # requires 8.2 & higher

class Launchpad(ControlSurface):

	_active_instances = []

	def __init__(self, c_instance):
		ControlSurface.__init__(self, c_instance)
		live = Live.Application.get_application()
		self._live_major_version = live.get_major_version()
		self._live_minor_version = live.get_minor_version()
		self._live_bugfix_version = live.get_bugfix_version()
		self._selector = None #needed because update hardware is called.
		self._mk2_rgb = False
		self.fixed_mode = False
		with self.component_guard():
			self._suppress_send_midi = True
			self._suppress_session_highlight = True
			self._suggested_input_port = ("InToLive")
			self._suggested_output_port = ("OutOfLive")
			self._control_is_with_automap = False
			self._user_byte_write_button = None
			self._config_button = None
			self._wrote_user_byte = False
			self._challenge = Live.Application.get_random_int(0, 400000000) & 2139062143
			self._init_done = False
		# caller will send challenge and we will continue as challenge is received.


	def init(self):
		#skip init if already done.
		if self._init_done:
			return
		self._init_done = True

		# second part of the __init__ after model has been identified using its challenge response
		if self._mk2_rgb:
			from SkinMK2 import make_skin
			self._skin = make_skin()
			self._side_notes = (89, 79, 69, 59, 49, 39, 29, 19)
			#self._drum_notes = (20, 30, 31, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102, 103, 112, 113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 124, 125, 126)
			self._drum_notes = (20, 30, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102, 103, 112, 113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 124, 125, 126)
		else:
			from SkinMK1 import make_skin # @Reimport
			self._skin = make_skin()
			self._side_notes = (8, 24, 40, 56, 72, 88, 104, 120)
			self._drum_notes = (41, 42, 43, 44, 45, 46, 47, 57, 58, 59, 60, 61, 62, 63, 73, 74, 75, 76, 77, 78, 79, 89, 90, 91, 92, 93, 94, 95, 105, 106, 107)

		with self.component_guard():
			is_momentary = True
			self._config_button = ButtonElement(is_momentary, MIDI_CC_TYPE, 0, 0, optimized_send_midi=False)
			self._config_button.add_value_listener(self._config_value)
			self._user_byte_write_button = ButtonElement(is_momentary, MIDI_CC_TYPE, 0, 16)
			self._user_byte_write_button.name = 'User_Byte_Button'
			self._user_byte_write_button.send_value(1)
			self._user_byte_write_button.add_value_listener(self._user_byte_value)
			matrix = ButtonMatrixElement()
			matrix.name = 'Button_Matrix'
			for row in range(8):
				button_row = []
				for column in range(8):
					if self._mk2_rgb:
						# for mk2 buttons are assigned "top to bottom"
						midi_note = (81 - (10 * row)) + column
					else:
						midi_note = row * 16 + column
					button = ConfigurableButtonElement(is_momentary, MIDI_NOTE_TYPE, 0, midi_note,row,column, skin = self._skin, control_surface = self)
					button.name = str(column) + '_Clip_' + str(row) + '_Button'
					button_row.append(button)
				matrix.add_row(tuple(button_row))

			top_buttons = [ConfigurableButtonElement(is_momentary, MIDI_CC_TYPE, 0, 104 + index,0,0, skin = self._skin) for index in range(8)]
			side_buttons = [ConfigurableButtonElement(is_momentary, MIDI_NOTE_TYPE, 0, self._side_notes[index],0,0, skin = self._skin) for index in range(8)]
			top_buttons[0].name = 'Bank_Select_Up_Button'
			top_buttons[1].name = 'Bank_Select_Down_Button'
			top_buttons[2].name = 'Bank_Select_Left_Button'
			top_buttons[3].name = 'Bank_Select_Right_Button'
			top_buttons[4].name = 'Session_Button'
			top_buttons[5].name = 'User1_Button'
			top_buttons[6].name = 'User2_Button'
			top_buttons[7].name = 'Mixer_Button'
			side_buttons[0].name = 'Vol_Button'
			side_buttons[1].name = 'Pan_Button'
			side_buttons[2].name = 'SndA_Button'
			side_buttons[3].name = 'SndB_Button'
			side_buttons[4].name = 'Stop_Button'
			side_buttons[5].name = 'Trk_On_Button'
			side_buttons[6].name = 'Solo_Button'
			side_buttons[7].name = 'Arm_Button'
			self._osd = M4LInterface()
			self._osd.name = "OSD"
			self._init_note_repeat()
			self._selector = MainSelectorComponent(matrix, tuple(top_buttons), tuple(side_buttons), self._config_button, self._osd, self, self._note_repeat)
			self._selector.name = 'Main_Modes'
			self._do_combine()
			for control in self.controls:
				if isinstance(control, ConfigurableButtonElement):
					control.add_value_listener(self._button_value)

			self._suppress_session_highlight = False
			self.set_highlighting_session_component(self._selector.session_component())
			# due to our 2 stage init, we need to rebuild midi map
			self.request_rebuild_midi_map()
			# and request update
			self._selector.update()
			if self._mk2_rgb:
				self.log_message("LaunchPad95 (AliveInVR fork) Loaded !")
			else:
				self.log_message("LaunchPad95 Loaded !")
		
		song = self.song()
		song.add_record_mode_listener(self._record_mode_listener)
		song.add_is_playing_listener(self._is_playing_listener)
		song.add_metronome_listener(self._metronome_listener)
		song.add_midi_recording_quantization_listener(self._midi_recording_quantization_listener)
		song.add_session_automation_record_listener(self._session_automation_record_listener)

	def disconnect(self):
		self._suppress_send_midi = True
		for control in self.controls:
			if isinstance(control, ConfigurableButtonElement):
				control.remove_value_listener(self._button_value)
		self._do_uncombine()
		if self._selector != None:
			self._user_byte_write_button.remove_value_listener(self._user_byte_value)
			self._config_button.remove_value_listener(self._config_value)
		ControlSurface.disconnect(self)
		self._suppress_send_midi = False
		if self._mk2_rgb:
			# launchpad mk2 needs disconnect string sent
			self._send_midi((240, 0, 32, 41, 2, 24, 64, 247))
		if self._config_button != None:
			self._config_button.send_value(32)#Send enable flashing led config message to LP
			self._config_button.send_value(0)
			self._config_button = None
		self._user_byte_write_button.send_value(0)
		self._user_byte_write_button = None

	def _combine_active_instances():
		support_devices = False
		for instance in Launchpad._active_instances:
			support_devices |= (instance._device_component != None)
		offset = 0
		for instance in Launchpad._active_instances:
			instance._activate_combination_mode(offset, support_devices)
			offset += instance._selector._session.width()

	_combine_active_instances = staticmethod(_combine_active_instances)

	def _activate_combination_mode(self, track_offset, support_devices):
		if(Settings.STEPSEQ__LINK_WITH_SESSION):
			self._selector._stepseq.link_with_step_offset(track_offset)
		if(Settings.SESSION__LINK):
			self._selector._session.link_with_track_offset(track_offset)

	def _do_combine(self):
		if (DO_COMBINE and (self not in Launchpad._active_instances)):
			Launchpad._active_instances.append(self)
			Launchpad._combine_active_instances()

	def _do_uncombine(self):
		if self in Launchpad._active_instances:
			Launchpad._active_instances.remove(self)
			if(Settings.SESSION__LINK):
				self._selector._session.unlink()
			if(Settings.STEPSEQ__LINK_WITH_SESSION):
				self._selector._stepseq.unlink()
			Launchpad._combine_active_instances()

	def refresh_state(self):
		ControlSurface.refresh_state(self)
		self.schedule_message(5, self._update_hardware)

	def handle_sysex(self, midi_bytes):
		# MK2 has different challenge and params jim changed to 17 byte device ID response
		if len(midi_bytes) == 17 and midi_bytes[:8] == (240, 126, 1, 6, 2,0, 32, 41):
						self._mk2_rgb = True
						self.log_message("Challenge Response ok (mk2)")
						self.log_message("AliveInVR detected")
						self._suppress_send_midi = False
						self.set_enabled(True)
						self.init()
						#send initial states 
						self._report_all_transport_states()
		else:
			if len(midi_bytes) == 17 and midi_bytes[:8] == (240, 126, 1, 6, 2,0, 32, 61):
				self.handle_aliveinvr_sysex_command(midi_bytes)
			else:
				ControlSurface.handle_sysex(self,midi_bytes)

	class ALIVEINVR_SYSEX_TRANSPORT_COMMAND:
			STOP_ALL_CLIPS = 0
			PLAY = 1
			STOP = 2
			RECORD_ALL = 3
			METRONOME_TOGGLE = 4
			RECORD_QUANTIZE = 5
			DUPLICATE = 6
			NEW = 7
			FIXED = 8
			AUTOMATION_REC = 9
			UNDO = 10
			REDO = 11
			SESSION_RECORD = 12
	
	class ALIVEINVR_SYSEX_COMMAND:
			TRANSPORT = 0

	def handle_aliveinvr_transport_command(self, command, value):
		
		CommandLookup = self.ALIVEINVR_SYSEX_TRANSPORT_COMMAND()
		
		song = self.song()
		if command == CommandLookup.STOP_ALL_CLIPS:
			song.stop_all_clips(False)
		elif command == CommandLookup.PLAY:
			song.start_playing()
		elif command == CommandLookup.STOP:
			song.stop_playing()
		elif command == CommandLookup.RECORD_ALL:
			song.record_mode = not song.record_mode
		elif command == CommandLookup.METRONOME_TOGGLE:
			song.metronome = not song.metronome
		elif command == CommandLookup.RECORD_QUANTIZE:
			song.midi_recording_quantization = value
		elif command == CommandLookup.DUPLICATE:
			song.capture_and_insert_scene()
		elif command == CommandLookup.NEW:
			song.capture_and_insert_scene(Live.Song.CaptureMode.all_except_selected)
		elif command == CommandLookup.FIXED:
			self.fixed_mode = not self.fixed_mode
			self._is_fixed_record_listener()
		elif command == CommandLookup.AUTOMATION_REC:
			song.session_automation_record = not song.session_automation_record
		elif command == CommandLookup.UNDO:
			song.undo()
		elif command == CommandLookup.REDO:
			song.redo()
		elif command == CommandLookup.SESSION_RECORD:
			self._selector._instrument_controller._track_controller._toggle_record_session()


	def handle_aliveinvr_sysex_command(self, midi_bytes):
		#first 8 bytes is header
		#byte 9 message type
		#rest are data depending on message type
	
		if midi_bytes[8] == self.ALIVEINVR_SYSEX_COMMAND.TRANSPORT:
			self.handle_aliveinvr_transport_command(midi_bytes[9], midi_bytes[10])


	def build_midi_map(self, midi_map_handle):
		ControlSurface.build_midi_map(self, midi_map_handle)
		if self._selector!=None:
			if self._selector._main_mode_index==2 or self._selector._main_mode_index==1:
				mode = Settings.USER_MODES[ (self._selector._main_mode_index-1) * Settings.USER_MODE_WIDTH + self._selector._sub_mode_list[self._selector._main_mode_index] ]
				#self._selector.mode_index == 1:
				#if self._selector._sub_mode_list[self._selector._mode_index] > 0:  # disable midi map rebuild for instrument mode to prevent light feedback errors
				if mode != "instrument":
					new_channel = self._selector.channel_for_current_mode()
					for note in self._drum_notes:
						self._translate_message(MIDI_NOTE_TYPE, note, 0, note, new_channel)

	def _send_midi(self, midi_bytes, optimized=None):
		sent_successfully = False
		if not self._suppress_send_midi:
			sent_successfully = ControlSurface._send_midi(self, midi_bytes, optimized=optimized)
		return sent_successfully

	def _update_hardware(self):
		self._suppress_send_midi = False
		if self._user_byte_write_button != None:
			self._user_byte_write_button.send_value(1)
			self._wrote_user_byte = True
		self._suppress_send_midi = True
		self.set_enabled(False)
		self._suppress_send_midi = False
		self._send_challenge()

	def _send_challenge(self):
		# send challenge for all models to allow to detect which one is actually plugged
		# mk2
		challenge_bytes = tuple([ self._challenge >> 8 * index & 127 for index in xrange(4) ])
		self._send_midi((240, 0, 32, 41, 2, 24, 64) + challenge_bytes + (247,))
		# mk1's
		for index in range(4):
			challenge_byte = self._challenge >> 8 * index & 127
			self._send_midi((176, 17 + index, challenge_byte))

	def _user_byte_value(self, value):
		assert (value in range(128))
		if not self._wrote_user_byte:
			enabled = (value == 1)
			self._control_is_with_automap = not enabled
			self._suppress_send_midi = self._control_is_with_automap
			if not self._control_is_with_automap:
				for control in self.controls:
					if isinstance(control, ConfigurableButtonElement):
						control.force_next_send()

			self._selector.set_mode(0)
			self.set_enabled(enabled)
			self._suppress_send_midi = False
		else:
			self._wrote_user_byte = False

	def _button_value(self, value):
		assert value in range(128)

	def _config_value(self, value):
		assert value in range(128)

	def _set_session_highlight(self, track_offset, scene_offset, width, height, include_return_tracks):
		if not self._suppress_session_highlight:
			ControlSurface._set_session_highlight(self, track_offset, scene_offset, width, height, include_return_tracks)

	def _init_note_repeat(self):
		self._note_repeat = NoteRepeatComponent(name='Note_Repeat')
		self._note_repeat.set_enabled(False)
		self._note_repeat.set_note_repeat(self._c_instance.note_repeat)

	def _report_transport_state(self, mode, value):
		ControlSurface._send_midi(self, (240, 0, 32, 41, 2, 24, 60) + (self.ALIVEINVR_SYSEX_COMMAND.TRANSPORT, mode, value) + (247,), None)
				
	def _record_mode_listener(self):
		self._report_transport_state(self.ALIVEINVR_SYSEX_TRANSPORT_COMMAND.RECORD_ALL, self.song().record_mode)
	
	def _is_playing_listener(self):
		self._report_transport_state(self.ALIVEINVR_SYSEX_TRANSPORT_COMMAND.PLAY, self.song().is_playing)
	
	def _metronome_listener(self):
		self._report_transport_state(self.ALIVEINVR_SYSEX_TRANSPORT_COMMAND.METRONOME_TOGGLE,self.song().metronome)
	
	def _midi_recording_quantization_listener(self):
		self._report_transport_state(self.ALIVEINVR_SYSEX_TRANSPORT_COMMAND.RECORD_QUANTIZE,self.song().midi_recording_quantization)
	
	def _session_automation_record_listener(self):
		self._report_transport_state(self.ALIVEINVR_SYSEX_TRANSPORT_COMMAND.AUTOMATION_REC,self.song().session_automation_record)

	def _is_fixed_record_listener(self):
		self._report_transport_state(self.ALIVEINVR_SYSEX_TRANSPORT_COMMAND.FIXED,self.fixed_mode)

	def _report_all_transport_states(self):
		self._record_mode_listener()
		self._is_playing_listener()
		self._metronome_listener()
		self._midi_recording_quantization_listener()
		self._session_automation_record_listener()
		self._is_fixed_record_listener()