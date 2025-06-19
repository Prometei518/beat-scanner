import time
import pygame
import numpy as np
from pydub import AudioSegment
from pydub.playback import play
import sounddevice as sd
import librosa
import threading

class BPMCorrector:
    def __init__(self):
        self.current_bpm = None
        self.reference_bpm = None
        self.lag_ms = 0.0  # Инициализируем как float
        self.is_playing = False
        self.audio_data = None
        self.sample_rate = 44100
        self.corrected_audio = None
        
    def calculate_bpm_from_taps(self):
        """Рассчитывает BPM на основе ручного ввода"""
        taps = []
        print("Нажимайте пробел в ритме музыки (минимум 4 раза). Для выхода нажмите Esc")
        
        pygame.init()
        screen = pygame.display.set_mode((300, 100))
        pygame.display.set_caption("BPM Calculator")
        
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        taps.append(time.time())
                        print(f"Tap {len(taps)}")
                    elif event.key == pygame.K_ESCAPE:
                        running = False
            
            if len(taps) >= 4:
                running = False
        
        if len(taps) < 2:
            print("Недостаточно нажатий для расчета BPM")
            return None
        
        intervals = np.diff(taps)  # Более эффективный способ расчета интервалов
        avg_interval = float(np.mean(intervals))  # Явное преобразование в float
        return 60.0 / avg_interval

    def calculate_bpm_from_audio(self, audio_data=None, file_path=None):
        """Анализирует аудио для определения BPM"""
        if file_path:
            try:
                y, sr = librosa.load(file_path)
                self.audio_data = y
                self.sample_rate = sr
            except Exception as e:
                print(f"Ошибка загрузки файла: {e}")
                return None
        elif audio_data is not None:
            y = audio_data
            sr = self.sample_rate
        else:
            print("Необходимо указать либо аудиоданные, либо путь к файлу")
            return None
        
        tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
        self.current_bpm = float(tempo)  # Явное преобразование в float
        return self.current_bpm

    def calculate_lag(self, reference_bpm):
        """Рассчитывает задержку для синхронизации"""
        if self.current_bpm is None or reference_bpm == 0:
            return 0.0
        
        self.reference_bpm = float(reference_bpm)
        reference_interval = 60000.0 / self.reference_bpm  # ms per beat
        current_interval = 60000.0 / self.current_bpm
        self.lag_ms = float(reference_interval - current_interval)  # Явное преобразование
        return self.lag_ms

    def time_stretch_audio(self, rate_change):
        """Изменяет темп аудио без изменения pitch"""
        if self.audio_data is None:
            print("Аудиоданные не загружены")
            return None
            
        n_fft = 2048
        hop_length = n_fft // 4
        
        stft = librosa.stft(self.audio_data, n_fft=n_fft, hop_length=hop_length)
        stft_stretched = librosa.phase_vocoder(stft, rate=rate_change, hop_length=hop_length)
        y_stretched = librosa.istft(stft_stretched, hop_length=hop_length)
        
        self.corrected_audio = y_stretched
        return y_stretched

    def auto_correct_tempo(self):
        """Автоматически корректирует темп под эталонный BPM"""
        if self.current_bpm is None or self.reference_bpm is None:
            print("Сначала определите текущий и эталонный BPM")
            return False
        
        if self.audio_data is None:
            print("Аудиоданные не загружены")
            return False
        
        rate_change = float(self.current_bpm / self.reference_bpm)
        print(f"Корректируем темп с коэффициентом {rate_change:.4f}")
        
        self.time_stretch_audio(rate_change)
        self.current_bpm = self.reference_bpm
        self.lag_ms = 0.0
        return True

    def play_original_audio(self):
        """Воспроизводит оригинальное аудио"""
        if self.audio_data is not None:
            self.is_playing = True
            sd.play(self.audio_data, self.sample_rate)
            sd.wait()
            self.is_playing = False

    def play_corrected_audio(self):
        """Воспроизводит скорректированное аудио"""
        if self.corrected_audio is not None:
            self.is_playing = True
            sd.play(self.corrected_audio, self.sample_rate)
            sd.wait()
            self.is_playing = False

    def stop_playback(self):
        """Останавливает воспроизведение"""
        sd.stop()
        self.is_playing = False

    def record_audio(self, duration=5):
        """Записывает аудио с микрофона"""
        print(f"Запись аудио в течение {duration} секунд...")
        self.audio_data = sd.rec(int(duration * self.sample_rate), 
                                samplerate=self.sample_rate, 
                                channels=1)
        sd.wait()
        print("Запись завершена")
        self.audio_data = np.squeeze(self.audio_data)
        return self.audio_data

def main():
    corrector = BPMCorrector()
    
    while True:
        print("\nМеню:")
        print("1 - Определить BPM (ручной ввод)")
        print("2 - Определить BPM (анализ аудиофайла)")
        print("3 - Записать аудио с микрофона")
        print("4 - Рассчитать задержку")
        print("5 - Автоматическая коррекция темпа")
        print("6 - Воспроизвести оригинальное аудио")
        print("7 - Воспроизвести скорректированное аудио")
        print("8 - Остановить воспроизведение")
        print("0 - Выход")
        
        choice = input("Ваш выбор: ")
        
        if choice == '1':
            bpm = corrector.calculate_bpm_from_taps()
            if bpm is not None:
                print(f"Определенный BPM: {bpm:.2f}")
                corrector.current_bpm = bpm
        
        elif choice == '2':
            file_path = input("Введите путь к аудиофайлу: ")
            bpm = corrector.calculate_bpm_from_audio(file_path=file_path)
            if bpm is not None:
                print(f"Определенный BPM: {bpm:.2f}")
        
        elif choice == '3':
            try:
                duration = float(input("Длительность записи (секунды): "))
                corrector.record_audio(duration)
                bpm = corrector.calculate_bpm_from_audio()
                if bpm is not None:
                    print(f"Определенный BPM: {bpm:.2f}")
            except ValueError:
                print("Ошибка: введите числовое значение для длительности")
        
        elif choice == '4':
            if corrector.current_bpm is None:
                print("Сначала определите текущий BPM")
                continue
            try:
                reference_bpm = float(input("Введите эталонный BPM: "))
                lag = corrector.calculate_lag(reference_bpm)
                print(f"Задержка: {lag:.2f} мс")
            except ValueError:
                print("Ошибка: введите числовое значение для BPM")
        
        elif choice == '5':
            if corrector.auto_correct_tempo():
                print("Темп успешно скорректирован!")
            else:
                print("Не удалось скорректировать темп")
        
        elif choice == '6':
            threading.Thread(target=corrector.play_original_audio).start()
        
        elif choice == '7':
            threading.Thread(target=corrector.play_corrected_audio).start()
        
        elif choice == '8':
            corrector.stop_playback()
        
        elif choice == '0':
            corrector.stop_playback()
            break
        
        else:
            print("Неверный выбор")

if __name__ == "__main__":
    main()