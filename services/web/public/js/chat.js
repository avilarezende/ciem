const USER_ID_KEY = "conversador_popse_user_id";

function getUserId() {
  let id = localStorage.getItem(USER_ID_KEY);
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem(USER_ID_KEY, id);
  }
  return id;
}

function addBubble(role, text) {
  const el = document.createElement("div");
  el.className = `bubble ${role}`;
  el.textContent = text;
  document.getElementById("messages").appendChild(el);
  el.scrollIntoView({ behavior: "smooth", block: "end" });
}

document.getElementById("chat-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const input = document.getElementById("message");
  const text = input.value.trim();
  if (!text) return;

  addBubble("user", text);
  input.value = "";
  input.disabled = true;

  try {
    const res = await fetch("/api/v1/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: text,
        user_id: getUserId(),
        channel: "web",
      }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    addBubble("assistant", data.reply);
  } catch (err) {
    addBubble(
      "assistant",
      "Peço desculpas, não foi possível processar sua mensagem no momento. Por favor, tente novamente em instantes ou contate o PoP-SE em info@pop-se.rnp.br."
    );
    console.error(err);
  } finally {
    input.disabled = false;
    input.focus();
  }
});

addBubble(
  "assistant",
  "Olá! Sou o Conversador PoP-SE. Estou à disposição para ajudá-lo com informações sobre conectividade, manutenções e situação dos links da sua instituição. Como posso ajudá-lo hoje?"
);
