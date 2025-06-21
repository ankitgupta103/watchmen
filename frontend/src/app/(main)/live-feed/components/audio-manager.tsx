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
      await this.createAlarmSound();
      this.isInitialized = true;
    } catch (error) {
      console.warn('Audio initialization failed:', error);
    }
  }

  private async createAlarmSound() {
    if (!this.audioContext) return;

    // Create a more urgent alarm sound
    const sampleRate = this.audioContext.sampleRate;
    const duration = 30; // seconds
    const buffer = this.audioContext.createBuffer(
      1,
      sampleRate * duration,
      sampleRate,
    );
    const data = buffer.getChannelData(0);

    for (let i = 0; i < buffer.length; i++) {
      const time = i / sampleRate;

      // Create a complex alarm sound with multiple frequencies
      const freq1 = 800 + Math.sin(time * 4) * 200; // Wobbling frequency
      const freq2 = 1200;
      const freq3 = 600;

      const wave1 = Math.sin(2 * Math.PI * freq1 * time);
      const wave2 = Math.sin(2 * Math.PI * freq2 * time);
      const wave3 = Math.sin(2 * Math.PI * freq3 * time);

      // Envelope for urgency
      const envelope = Math.pow(Math.sin((time * Math.PI) / duration), 0.5);

      // Mix the waves with envelope
      data[i] = (wave1 * 0.4 + wave2 * 0.3 + wave3 * 0.3) * envelope * 0.3;
    }

    this.alarmBuffer = buffer;
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
