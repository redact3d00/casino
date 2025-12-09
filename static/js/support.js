fetch('/api/support/tickets', { credentials: 'include' })
  .then(r => r.json())
  .then(d => {
    document.getElementById('tickets').innerHTML = d.tickets.map(t => `
      <div class="card mt-2">
        <h4>#${t.id} ${t.subject}</h4>
        <p>Статус: ${t.status} | ${new Date(t.created_at).toLocaleString()}</p>
        <a href="/support/ticket/${t.id}" class="btn btn-sm btn-info">Открыть</a>
      </div>
    `).join('');
  });

document.getElementById('new-ticket-form').onsubmit = async e => {
  e.preventDefault();
  const token = document.querySelector('input[name="csrf_token"]').value;
  await fetch('/api/support/tickets', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': token },
    body: JSON.stringify({
      subject: document.getElementById('subject').value,
      message: document.getElementById('message').value
    }),
    credentials: 'include'
  });
  alert('Тикет создан!');
  location.reload();
};