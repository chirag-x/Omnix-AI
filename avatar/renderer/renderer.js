const stateIndicator = document.getElementById('state-indicator');
const face = document.getElementById('face');
const eyes = document.querySelectorAll('.eye');
const mouth = document.getElementById('mouth');
const avatar = document.getElementById('diagnostic-avatar');

avatar.classList.add('breathing');

let ws;
let port = 21212; 

function connect() {
    ws = new WebSocket(`ws://127.0.0.1:${port}`);
    
    ws.onopen = () => {
        console.log("Connected to Omnix Avatar Bridge");
        ws.send(JSON.stringify({ protocol: 1, type: "renderer.ready" }));
    };

    ws.onmessage = (event) => {
        try {
            const msg = JSON.parse(event.data);
            if (msg.type === "avatar.state") {
                updateState(msg.payload);
            }
        } catch (e) {
            console.error("Invalid message", e);
        }
    };

    ws.onclose = () => {
        console.log("Disconnected. Reconnecting in 3s...");
        setTimeout(connect, 3000);
    };
}

const colors = {
    neutral: "rgba(200, 200, 255, 0.8)",
    happy: "rgba(255, 220, 100, 0.8)",
    excited: "rgba(255, 150, 100, 0.8)",
    sad: "rgba(150, 150, 200, 0.8)",
    confused: "rgba(200, 100, 200, 0.8)",
    angry: "rgba(255, 100, 100, 0.8)"
};

function updateState(payload) {
    const { operational_state, emotion, speech_state } = payload;
    stateIndicator.innerText = `${operational_state} | ${speech_state}`;
    
    if (colors[emotion]) {
        face.style.backgroundColor = colors[emotion];
    }

    if (operational_state === "sleeping") {
        eyes.forEach(e => e.style.height = '2px');
        avatar.style.animationDuration = '6s';
    } else {
        eyes.forEach(e => e.style.height = '20px');
        avatar.style.animationDuration = '4s';
    }

    if (speech_state === "speaking") {
        mouth.style.height = '15px';
        mouth.style.borderRadius = '50%';
        if (!window.speechAnim) {
            window.speechAnim = setInterval(() => {
                mouth.style.height = (Math.random() * 15 + 4) + 'px';
            }, 100);
        }
    } else {
        clearInterval(window.speechAnim);
        window.speechAnim = null;
        mouth.style.height = '4px';
        mouth.style.borderRadius = '10px';
    }
}

connect();
