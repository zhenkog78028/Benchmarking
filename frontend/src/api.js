const API = import.meta.env.VITE_API_URL || 'http://localhost:8000';
export async function getModels(){const r=await fetch(`${API}/api/models`); if(!r.ok) throw new Error('Could not load models'); return r.json();}
export async function startBenchmark(body){const r=await fetch(`${API}/api/benchmarks`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}); if(!r.ok) throw new Error((await r.json()).detail||'Could not start benchmark'); return r.json();}
export async function getBenchmark(id){const r=await fetch(`${API}/api/benchmarks/${id}`); if(!r.ok) throw new Error('Could not load benchmark'); return r.json();}
