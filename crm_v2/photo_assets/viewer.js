// Inline CCv2 renderer. No photo contents or directory handles are sent to Python.
export const normalize = value => String(value ?? '').normalize('NFD')
  .replace(/[\u0300-\u036f]/g, '').replace(/đ/g, 'd').replace(/Đ/g, 'D')
  .trim().replace(/\s+/g, ' ').toLowerCase();

export function safePart(value) {
  const part = String(value ?? '').trim();
  if (!part || part === '.' || part === '..' || /[\\/\0]/.test(part)) throw Error('Địa chỉ chưa đầy đủ hoặc không hợp lệ.');
  return part;
}

export async function childDirectory(parent, wanted) {
  const matches = [];
  for await (const [name, entry] of parent.entries()) {
    if (entry.kind === 'directory' && normalize(name) === normalize(wanted)) matches.push(entry);
  }
  if (matches.length !== 1) throw Error(matches.length ? `Có nhiều thư mục trùng tên: ${wanted}` : `Chưa có thư mục: ${wanted}`);
  return matches[0];
}

export async function validateRoot(root) {
  if (normalize(root.name) !== 'sh total') throw Error('Hãy chọn đúng thư mục SH Total.');
  await childDirectory(root, 'Binh Thanh');
  await childDirectory(root, 'Phu Nhuan');
  return root;
}

export async function houseImages(root, request) {
  const district = await childDirectory(root, safePart(request.district));
  const street = safePart(request.street), number = safePart(request.number);
  const road = await childDirectory(district, street);
  const house = await childDirectory(road, `${number} ${street}`);
  const files = [];
  // House JPGs only: SF and other nested folders are intentionally excluded.
  for await (const [name, entry] of house.entries()) {
    if (entry.kind === 'file' && /\.jpe?g$/i.test(name)) files.push(entry);
  }
  files.sort((a,b) => a.name.localeCompare(b.name, 'vi', {numeric:true}));
  if (!files.length) throw Error('Thư mục này chưa có ảnh JPG.');
  return files;
}

export function cloudURL(value) {
  try { const url = new URL(value); return url.protocol === 'https:' ? url.href : ''; }
  catch { return ''; }
}

function dbAccess(mode, value) {
  return new Promise((resolve, reject) => {
    const open = indexedDB.open('dtk-crm-v2-photos', 1);
    open.onupgradeneeded = () => open.result.createObjectStore('settings');
    open.onerror = () => reject(open.error);
    open.onsuccess = () => {
      const db = open.result, tx = db.transaction('settings', mode === 'get' ? 'readonly' : 'readwrite');
      const store = tx.objectStore('settings');
      const op = mode === 'get' ? store.get('root') : mode === 'delete' ? store.delete('root') : store.put(value, 'root');
      let result;
      op.onsuccess = () => { result = op.result; };
      tx.oncomplete = () => { db.close(); resolve(result); };
      tx.onerror = () => { db.close(); reject(tx.error); };
      tx.onabort = () => { db.close(); reject(tx.error || Error('Không lưu được quyền thư mục.')); };
    };
  });
}

const instances = new WeakMap();
export default function(component) {
  const {parentElement, data} = component;
  let s = instances.get(parentElement);
  if (!s) {
    const host = parentElement.querySelector('#photos');
    host.innerHTML = `<h3>Ảnh trên thiết bị</h3><div class="toolbar"><button class="choose">Chọn SH Total</button>
      <button class="grant">Cấp lại quyền</button><button class="forget">Quên thư mục</button></div>
      <p class="status" role="status">Chọn SH Total đã đồng bộ về thiết bị; khi thiếu ảnh sẽ dùng link Cloud.</p>
      <h4 class="address"></h4><button class="reopen" hidden>Mở lại ảnh nhà này</button>
      <a class="cloud" hidden target="_blank" rel="noopener noreferrer">Mở ảnh Cloud</a>
      <div class="viewer" hidden><img alt="Ảnh nhà"><nav><button class="prev">←</button><span></span>
      <button class="next">→</button><button class="close">Đóng ảnh lớn</button></nav></div><div class="gallery"></div>`;
    s = {host, root:null, urls:[], generation:0, disposed:false, request:null, index:0, ready:null};
    instances.set(parentElement,s);
    const $ = selector => host.querySelector(selector);
    const status = text => { $('.status').textContent = text; };
    const clear = () => {
      s.generation++;
      for (const url of s.urls) URL.revokeObjectURL(url);
      s.urls = []; $('.gallery').replaceChildren(); $('.viewer').hidden = true;
      $('.viewer img').removeAttribute('src');
    };
    const fallback = message => {
      const link = cloudURL(s.request?.drive_url);
      status(link ? `${message} Dùng ảnh Cloud qua liên kết bên dưới.` : `${message} Chưa có ảnh Cloud.`);
      $('.cloud').hidden = !link;
      if (link) {
        $('.cloud').href = link;
        // Browsers may block this after a server round trip. Keep the explicit link.
        let alreadyOpened = false;
        try {
          const key = 'dtk-crm-v2-last-cloud-request';
          alreadyOpened = sessionStorage.getItem(key) === String(s.request.nonce);
          sessionStorage.setItem(key, String(s.request.nonce));
        } catch { /* Storage is optional; photo permissions remain browser-owned. */ }
        if (!alreadyOpened) window.open(link, '_blank', 'noopener,noreferrer');
      }
    };
    const enlarge = index => {
      s.index = (index + s.urls.length) % s.urls.length;
      $('.viewer img').src = s.urls[s.index];
      $('.viewer span').textContent = `${s.index+1} / ${s.urls.length}`;
      $('.viewer').hidden = false;
      $('.viewer').scrollIntoView({block:'nearest'});
    };
    s.open = async request => {
      clear(); s.request = request;
      if (!request) return;
      const generation = s.generation;
      $('.reopen').hidden = false;
      $('.address').textContent = `${request.number} ${request.street} · ${request.district}`;
      host.scrollIntoView({behavior:'smooth',block:'start'});
      $('.cloud').hidden = true;
      status('Đang tìm ảnh trên thiết bị…');
      await s.ready;
      try {
        if (!s.root) throw Error('Chưa chọn thư mục ảnh trên thiết bị.');
        if (await s.root.queryPermission({mode:'read'}) !== 'granted') throw Error('Cần bấm Cấp lại quyền để đọc ảnh.');
        const files = await houseImages(s.root, request);
        for (const handle of files) {
          const file = await handle.getFile();
          if (s.disposed || generation !== s.generation) return;
          const url = URL.createObjectURL(file); s.urls.push(url);
          const image = document.createElement('img');
          image.src = url; image.alt = handle.name; image.loading = 'lazy';
          const i = s.urls.length-1; image.onclick = () => enlarge(i);
          $('.gallery').append(image);
        }
        if (generation === s.generation) status(`Đã mở ${s.urls.length} ảnh JPG từ thiết bị. Bấm ảnh để phóng lớn, vuốt để chuyển ảnh.`);
      } catch(e) { if (!s.disposed && generation === s.generation) fallback(e.message); }
    };
    $('.choose').onclick = async () => {
      if (!window.isSecureContext || !window.showDirectoryPicker) {
        status('Trình duyệt này chưa hỗ trợ chọn thư mục. Hãy dùng Chrome mới qua HTTPS; ảnh Cloud vẫn dùng được.'); return;
      }
      try {
        const root = await showDirectoryPicker({id:'dtk-crm-v2',mode:'read'});
        await validateRoot(root); s.root = root;
        let remembered = true;
        try { await dbAccess('put',root); } catch { remembered = false; }
        status(remembered ? 'OK: SH Total có Bình Thạnh và Phú Nhuận. Đã ghi nhớ thư mục trên trình duyệt này.' : 'OK: thư mục hợp lệ. Trình duyệt không lưu được quyền; lần sau cần chọn lại.');
        if (s.request) await s.open(s.request);
      } catch(e) { if (e.name !== 'AbortError') status(e.message); }
    };
    $('.grant').onclick = async () => {
      try {
        if (!s.root) { status('Hãy chọn SH Total trước.'); return; }
        if (await s.root.requestPermission({mode:'read'}) !== 'granted') throw Error('Chưa được cấp quyền đọc ảnh.');
        await validateRoot(s.root); status('OK: quyền đọc ảnh đã được cấp.');
        if (s.request) await s.open(s.request);
      } catch(e) { status(e.message); }
    };
    $('.forget').onclick = async () => {
      clear(); s.root = null;
      try { await dbAccess('delete'); status('Đã quên thư mục. Ảnh trên thiết bị vẫn được giữ nguyên.'); }
      catch { status('Không xóa được quyền đã lưu. Hãy xóa dữ liệu trang trong trình duyệt.'); }
    };
    $('.reopen').onclick = () => s.open(s.request);
    $('.prev').onclick = () => enlarge(s.index-1);
    $('.next').onclick = () => enlarge(s.index+1);
    $('.close').onclick = () => { $('.viewer').hidden = true; };
    let touchX = null;
    $('.viewer img').ontouchstart = e => { touchX = e.touches.length === 1 ? e.touches[0].clientX : null; };
    $('.viewer img').ontouchend = e => {
      if (touchX !== null && e.changedTouches.length === 1) {
        const dx = e.changedTouches[0].clientX-touchX;
        if (Math.abs(dx)>60) enlarge(s.index+(dx<0 ? 1 : -1));
      }
      touchX = null;
    };
    s.clear = clear;
    s.ready = (async () => {
      try {
        s.root = await dbAccess('get');
        if (!s.root) return;
        const allowed = await s.root.queryPermission({mode:'read'}) === 'granted';
        status(allowed ? 'Đã khôi phục thư mục SH Total trên thiết bị.' : 'Đã nhớ thư mục. Bấm Cấp lại quyền để xem ảnh.');
      } catch { status('Chọn SH Total để xem ảnh trên thiết bị này.'); }
    })();
  }
  if (data?.request && s.request?.nonce !== data.request.nonce) s.open(data.request);
  return () => { s.disposed = true; s.clear(); instances.delete(parentElement); };
}
