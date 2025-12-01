self.addEventListener('install', (event) => {
  console.log('Service Worker installing.');
});

self.addEventListener('fetch', (event) => {
  // Basic pass-through fetch for now. 
  // In future, we can cache assets here for offline use.
  event.respondWith(fetch(event.request));
});
