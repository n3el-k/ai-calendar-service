const button = document.getElementById('btn');
const textArea = document.getElementById("text-area");
const list = document.getElementById("list");

// "2026-10-22T15:00:00" -> "Oct 22, 2026, 3:00 PM"
function formatTime(iso) {
    return new Date(iso).toLocaleString([], {dateStyle: "medium", timeStyle: "short"});
}

async function renderEvents() {
    const response = await fetch('/events');
    const data = await response.json();
    const dataList = Object.entries(data);
    list.replaceChildren();

    if (dataList.length == 0) {
        const item = document.createElement("li");
        item.textContent = "No upcoming events";
        list.appendChild(item);
    }

    for (const [id, e] of dataList) {

        const item = document.createElement('li');
        const delButton = document.createElement("button");
        const span = document.createElement("span");

        span.textContent = e.title + " (" + formatTime(e.start_day_time) + ") ";
        delButton.textContent = "Delete";

        delButton.addEventListener("click", async () => {
            await fetch("/events/" + id, {method: "DELETE"});
            renderEvents();
        })

        item.appendChild(span);
        item.appendChild(delButton);
        list.appendChild(item);
    }
}

async function renderPending() {
    const pendingDiv = document.getElementById("pending");
    const response = await fetch('/pending');
    const data = await response.json();
    console.log(data);

    pendingDiv.replaceChildren();
    const pending = data.pending;
    if (pending === null) return;

    const info = document.createElement("span");
    const cancelButton = document.createElement("button");
    const confirmButton = document.createElement("button");

    cancelButton.textContent = "Cancel";
    confirmButton.textContent = "Confirm";

    const title = document.createElement("p"), time = document.createElement("p");
    title.textContent = pending.event.title;
    time.textContent = formatTime(pending.event.start_day_time);

    confirmButton.addEventListener("click", async () => {
        const res = await fetch("/pending/confirm", {method: "POST"});
        if (!res.ok) {
            const err = await res.json();
            alert(JSON.stringify(err.detail));
        }
        renderPending();
        renderEvents();
    });

    cancelButton.addEventListener("click", async () => {
        await fetch("/pending", {method: "DELETE"});
        renderPending();
        renderEvents();
    });

    info.appendChild(title);
    info.appendChild(time);
    pendingDiv.appendChild(info);
    pendingDiv.appendChild(confirmButton);
    pendingDiv.appendChild(cancelButton);
}

async function clickListener() {
    const text = textArea.value;
    const response = await fetch('/command', {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
            request: text
        })});
        
    const data = await response.json()
    if (!response.ok) {
        alert(JSON.stringify(data.detail));
        return;
    }
    textArea.value = "";
    renderEvents();
    renderPending();
}
renderPending();
renderEvents();
button.addEventListener("click", clickListener);
