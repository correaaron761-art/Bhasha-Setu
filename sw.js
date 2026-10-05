const C='bhasha-setu-v13',P='bhasa-setu-pdf';
const CORE=['./','./index.html','./manifest.json','./sw.js'];
const PDFS=[
 './primers/jharkhand/Aao_Santali_Likhna_Sikhe.pdf',
 './primers/jharkhand/Santali_Baal_Chitra_Pustak.pdf',
 './primers/jharkhand/Santali_Shabd_Mala_Book.pdf',
 './primers/jharkhand/Mawno_Bal_Pustika.pdf',
 './primers/jharkhand/Primer_Aasuri.pdf',
 './primers/jharkhand/Primer_Korwa.pdf',
 './primers/jharkhand/The_Parhaiya_Primer.pdf',
 './primers/jharkhand/The_Sabar_Primer.pdf',
 './dictionaries/Santali_Bilingual_Dictionary.pdf',
 './dictionaries/Santali_Trilingual_Dictionary.pdf',
 './dictionaries/Mundari_Hindi_Dictionary.pdf'
];
// Core app files are cached first (all-or-nothing); PDFs are cached best-effort so one missing PDF cannot block the app from working offline.
self.addEventListener('install',e=>{self.skipWaiting();e.waitUntil(caches.open(C).then(c=>c.addAll(CORE).then(()=>Promise.all(PDFS.map(p=>c.add(p).catch(()=>{}))))))});
self.addEventListener('activate',e=>e.waitUntil(caches.keys().then(k=>Promise.all(k.filter(x=>x!==C&&x!==P).map(x=>caches.delete(x)))).then(()=>self.clients.claim())));
self.addEventListener('fetch',e=>{const r=e.request;if(r.method!=='GET')return;if(/\.pdf($|\?)/.test(r.url)){e.respondWith(caches.match(r.url,{ignoreSearch:true}).then(m=>m||fetch(r)));return}e.respondWith(fetch(r).then(x=>{const cp=x.clone();caches.open(C).then(c=>c.put(r,cp)).catch(()=>{});return x}).catch(()=>caches.match(r)))});
