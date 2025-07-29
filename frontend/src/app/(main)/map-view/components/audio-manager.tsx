// Audio Manager
export class AudioManager {
  private audioContext: AudioContext | null = null;
  private alarmBuffer: AudioBuffer | null = null;
  private isInitialized = false;

  async initialize() {
    if (this.isInitialized) return;

    try {
      this.audioContext = new (window.AudioContext ||
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (window as any).webkitAudioContext)();
      await this.loadAlarmSound();
      this.isInitialized = true;
    } catch (error) {
      console.warn('Audio initialization failed:', error);
    }
  }

  private async loadAlarmSound() {
    if (!this.audioContext) return;

    try {
      // Fetch the siren.mp3 file from the public assets folder
      const response = await fetch('/assets/siren.mp3');
      const arrayBuffer = await response.arrayBuffer();
      this.alarmBuffer = await this.audioContext.decodeAudioData(arrayBuffer);
    } catch (error) {
      console.warn('Failed to load siren.mp3:', error);
    }
  }

  async playAlarm(volume: number = 0.5) {
    if (!this.audioContext || !this.alarmBuffer || !this.isInitialized) {
      await this.initialize();
      if (!this.audioContext || !this.alarmBuffer) return;
    }

    // Resume audio context if suspended (browser autoplay policy)
    if (this.audioContext.state === 'suspended') {
      await this.audioContext.resume();
    }

    const source = this.audioContext.createBufferSource();
    const gainNode = this.audioContext.createGain();

    source.buffer = this.alarmBuffer;
    source.connect(gainNode);
    gainNode.connect(this.audioContext.destination);
    gainNode.gain.setValueAtTime(volume, this.audioContext.currentTime);

    source.start();
  }
}
