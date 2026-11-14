import { apiFetch } from './api.js';

document.addEventListener('DOMContentLoaded', () => {
    const micBtn = document.getElementById('mic-btn');
    const userInputEl = document.getElementById('user-input');

    let mediaRecorder = null;
    let audioChunks = [];
    let isRecording = false;

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        if (micBtn) micBtn.style.display = 'none';
        console.warn('MediaRecorder API not supported in this browser.');
        return;
    }

    micBtn.addEventListener('click', async () => {
        if (!isRecording) {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
                audioChunks = [];

                mediaRecorder.ondataavailable = (event) => {
                    if (event.data.size > 0) {
                        audioChunks.push(event.data);
                    }
                };

                mediaRecorder.onstop = async () => {
                    const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
                    await sendAudioForTranscription(audioBlob);
                    
                    // Stop all microphone tracks
                    stream.getTracks().forEach(track => track.stop());
                };

                mediaRecorder.start();
                isRecording = true;
                micBtn.style.color = '#ef4444';
                micBtn.title = 'Recording... Click to stop';
            } catch (err) {
                console.error('Microphone permission denied or error:', err);
                alert('Microphone access was denied or is not supported.');
            }
        } else {
            if (mediaRecorder && mediaRecorder.state !== 'inactive') {
                mediaRecorder.stop();
            }
            isRecording = false;
            micBtn.style.color = '';
            micBtn.title = 'Voice Input';
        }
    });

    async function sendAudioForTranscription(blob) {
        const formData = new FormData();
        formData.append('file', blob, 'voice_input.webm');

        micBtn.style.opacity = '0.5';

        try {
            const res = await apiFetch('/api/v1/voice/transcribe', {
                method: 'POST',
                body: formData
            });

            if (res.ok) {
                const data = await res.json();
                if (data.text) {
                    userInputEl.value = userInputEl.value ? `${userInputEl.value} ${data.text}` : data.text;
                }
            } else {
                const errData = await res.json();
                alert(errData.detail || 'Transcription failed.');
            }
        } catch (err) {
            console.error('Transcription network error:', err);
            alert('Failed to connect to transcription service.');
        } finally {
            micBtn.style.opacity = '1';
        }
    }
});

// Export helper to attach TTS speaker button to assistant messages
export function attachTTSHandler(messageElement, textContent) {
    const headerDiv = document.createElement('div');
    headerDiv.className = 'message-header';

    const speakBtn = document.createElement('button');
    speakBtn.className = 'tts-speak-btn';
    speakBtn.innerHTML = '🔊';
    speakBtn.title = 'Read aloud';

    speakBtn.addEventListener('click', () => {
        if ('speechSynthesis' in window) {
            window.speechSynthesis.cancel(); // Stop any ongoing speech
            const utterance = new SpeechSynthesisUtterance(textContent);
            utterance.rate = 1.0;
            utterance.pitch = 1.0;
            window.speechSynthesis.speak(utterance);
        } else {
            alert('Speech synthesis is not supported in this browser.');
        }
    });

    headerDiv.appendChild(speakBtn);
    messageElement.insertBefore(headerDiv, messageElement.firstChild);
}