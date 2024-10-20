const form = document.getElementById('query-form');
const responseDiv = document.getElementById('response');

form.addEventListener('submit', async (event) => {
    event.preventDefault();
    responseDiv.innerHTML = '';
    const query = document.getElementById('query').value;
    const mode = document.querySelector('input[name="mode"]:checked').value;

    // Start the EventSource connection to the server stream
    const eventSource = new EventSource(`/stream?query=${encodeURIComponent(query)}&mode=${mode}`);

    eventSource.onmessage = function(event) {
        console.log("Received event data:", event.data);  // Debugging: log the data received from the server
        try {
            // Check if the data received is the [DONE] marker
            if (event.data === "[DONE]") {
                console.log("Stream completed.");
                eventSource.close();  // Close the stream when [DONE] is received
            } else {
                // Append the streamed data to the responseDiv
                responseDiv.insertAdjacentHTML('beforeend', event.data);
            }
        } catch (error) {
            console.error("Error handling streamed data:", error);
        }
    };

    eventSource.onerror = function(event) {
        console.error("EventSource error:", event);
        responseDiv.innerHTML += "<p><em>An error occurred. Please try again.</em></p>";
        eventSource.close();  // Always close the event source on error
    };

    eventSource.onopen = function() {
        console.log("Connection to server opened.");
    };
});
