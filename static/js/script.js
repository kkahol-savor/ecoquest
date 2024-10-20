const form = document.getElementById('query-form');
const chatBox = document.getElementById('chat-box');

let botMessageDiv = null;  // Keep track of the current bot message div to update

form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const query = document.getElementById('query').value;
    const mode = document.querySelector('input[name="mode"]:checked').value;

    if (query.trim() === "") return; // Prevent sending empty messages

    // Add the user's message to the chatbox
    appendMessage("user", query);
    document.getElementById('query').value = ''; // Clear the input

    // Reset the botMessageDiv for each new query to ensure each new response starts fresh
    botMessageDiv = null;

    const eventSource = new EventSource(`/stream?query=${encodeURIComponent(query)}&mode=${mode}`);

    eventSource.onmessage = function(event) {
        if (event.data === "[DONE]") {
            console.log("Stream completed.");
            eventSource.close();  // Close the stream when [DONE] is received
            botMessageDiv = null;  // Reset for the next message
        } else {
            // If we are still streaming, update the same bot message
            if (!botMessageDiv) {
                botMessageDiv = appendMessage("bot", event.data, true); // Create a new bot bubble
            } else {
                botMessageDiv.querySelector('.bubble').innerHTML += event.data;  // Append new content to the same bubble
            }
        }
    };

    eventSource.onerror = function(event) {
        console.error("EventSource error:", event);
        appendMessage("bot", "<em>An error occurred. Please try again.</em>");
        eventSource.close();
    };

    eventSource.onopen = function() {
        console.log("Connection to server opened.");
    };

    eventSource.onclose = function() {
        botMessageDiv = null;  // Reset when the stream is complete
    };
});

// Function to append messages to the chatbox
function appendMessage(sender, text, isStreaming = false) {
    const messageDiv = document.createElement('div');
    messageDiv.classList.add('message', sender);
    const bubble = document.createElement('div');
    bubble.classList.add('bubble');
    bubble.innerHTML = text;
    messageDiv.appendChild(bubble);
    chatBox.appendChild(messageDiv);
    chatBox.scrollTop = chatBox.scrollHeight; // Auto scroll to the bottom

    // Return the message div if we are streaming (to update it later)
    if (isStreaming) {
        return messageDiv;
    }
}
