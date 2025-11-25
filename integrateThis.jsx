function appendBlock(block) {
    // 1. Create the HTML wrapper based on block.role
    const wrapper = document.createElement('div');
    // ... (Use the same HTML generation logic as inside the renderFromJSON function above) ...

    // 2. Append to container
    document.getElementById('chat-container').appendChild(wrapper);

    // 3. Scroll to it
    wrapper.scrollIntoView({ behavior: 'smooth' });
}

// Usage with a WebSocket (Real-time)
const socket = new WebSocket('ws://your-agent-backend');

socket.onmessage = function (event) {
    const blockData = JSON.parse(event.data);
    appendBlock(blockData);
};