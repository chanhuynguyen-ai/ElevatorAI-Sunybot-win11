async function sendMessage() {
    const input = document.getElementById("user-input");
    const message = input.value.trim();
    if (!message) return;

    appendMessage("👤 Bạn: " + message, "user");
    input.value = "";

    const res = await fetch("/chat", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({question: message})
    });

    const data = await res.json();
    appendMessage(data.answer, "bot");
}

function appendMessage(text, cls) {
    const chatBox = document.getElementById("chat-box");
    const div = document.createElement("div");
    div.className = "message " + cls;
    div.innerText = text;
    chatBox.appendChild(div);
    chatBox.scrollTop = chatBox.scrollHeight;
}

