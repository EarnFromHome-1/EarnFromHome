async function spin(){const r=await fetch('/spin');const d=await r.json();document.getElementById('spinResult').textContent=d.message;}
