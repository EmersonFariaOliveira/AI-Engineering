html = """
<!DOCTYPE html>
<html>
    <head>
        <title>Chat</title>
        <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
        <style>
            body { font-family: Arial, sans-serif; padding: 20px; }
            .message-container { margin-top: 20px; }
            .assistant-message {
                background: #f5f5f5;
                border-radius: 6px;
                padding: 10px;
                margin-bottom: 10px;
                white-space: pre-wrap;
            }
            .user-message {
                background: #e0f7ff;
                border-radius: 6px;
                padding: 10px;
                margin-bottom: 10px;
                white-space: pre-wrap;
            }
        </style>
    </head>

    <body>
        <h1>WebSocket Chat (Markdown Enabled)</h1>

        <form onsubmit="sendMessage(event)">
            <input type="text" id="messageText" autocomplete="off"/>
            <button>Send</button>
        </form>

        <div id="messages" class="message-container"></div>

        <script>
            var ws = new WebSocket("ws://localhost:8000/ws/123");

            // buffer da resposta atual do assistente
            var currentAssistantDiv = null;
            var currentBuffer = "";

            ws.onmessage = function(event) {
                var messagesDiv = document.getElementById('messages');

                // se ainda não existe um "balão" para esta resposta, cria um
                if (!currentAssistantDiv) {
                    currentAssistantDiv = document.createElement("div");
                    currentAssistantDiv.className = "assistant-message";
                    messagesDiv.appendChild(currentAssistantDiv);
                }

                // acumula os chunks em um buffer
                currentBuffer += event.data;

                // renderiza o markdown do buffer completo
                currentAssistantDiv.innerHTML = marked.parse(currentBuffer);
            };

            function sendMessage(event) {
                var input = document.getElementById("messageText");
                var value = input.value;

                if (!value) {
                    event.preventDefault();
                    return;
                }

                var messagesDiv = document.getElementById('messages');

                // adiciona mensagem do usuário
                var userEl = document.createElement("div");
                userEl.className = "user-message";
                userEl.innerText = value;
                messagesDiv.appendChild(userEl);

                // envia para o backend
                ws.send(value);

                // reseta buffer da próxima resposta do assistente
                currentAssistantDiv = null;
                currentBuffer = "";

                input.value = '';
                event.preventDefault();
            }
        </script>
    </body>
</html>
"""
