import { initializeApp } from "firebase/app";
import { getFirestore, collection, addDoc, onSnapshot, query, orderBy, serverTimestamp, doc, updateDoc, increment } from "firebase/firestore";

// 1. AYARLAR (.env'den gelir)
const firebaseConfig = {
  apiKey: import.meta.env.VITE_API_KEY,
  authDomain: import.meta.env.VITE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_PROJECT_ID,
  storageBucket: import.meta.env.VITE_STORAGE_BUCKET,
  messagingSenderId: import.meta.env.VITE_MESSAGING_SENDER_ID,
  appId: import.meta.env.VITE_APP_ID
};

// 2. Başlatma
const app = initializeApp(firebaseConfig);
const db = getFirestore(app);

// 3. HTML Elemanları
const commentForm = document.getElementById('ghostyCommentForm');
const commentList = document.getElementById('commentList');
const noCommentsMsg = document.getElementById('noCommentsMsg');

// ---------------------------------------------------------
// A) VERİLERİ CANLI ÇEKME
// ---------------------------------------------------------
const q = query(collection(db, "comments"), orderBy("timestamp", "desc"));

onSnapshot(q, (snapshot) => {
    commentList.innerHTML = ""; // Listeyi temizle

    if (snapshot.empty) {
        if(noCommentsMsg) {
            noCommentsMsg.style.display = 'block';
            commentList.appendChild(noCommentsMsg);
        }
    } else {
        if(noCommentsMsg) noCommentsMsg.style.display = 'none';
        
        snapshot.forEach((document) => {
            const data = document.data();
            const docId = document.id;
            renderComment(docId, data);
        });
    }
});

// ---------------------------------------------------------
// B) YENİ YORUM EKLEME
// ---------------------------------------------------------
if (commentForm) {
    commentForm.addEventListener('submit', async function(e) {
        e.preventDefault();

        const usernameInput = document.getElementById('username');
        const commentInput = document.getElementById('usercomment');
        const submitBtn = commentForm.querySelector('button');
        
        let name = usernameInput.value.trim();
        const text = commentInput.value.trim();

        if(name === "") name = "Misafir Kullanıcı";

        if (text) {
            submitBtn.disabled = true;
            submitBtn.innerText = "Gönderiliyor...";

            try {
                const now = new Date();
                const dateString = now.toLocaleDateString('tr-TR');

                await addDoc(collection(db, "comments"), {
                    name: name,
                    text: text,
                    date: dateString,
                    timestamp: serverTimestamp(),
                    likes: 0,
                    dislikes: 0
                });

                // Formu temizle
                usernameInput.value = '';
                commentInput.value = '';

            } catch (error) {
                console.error("Hata:", error);
                alert("Yorum gönderilemedi.");
            } finally {
                submitBtn.disabled = false;
                submitBtn.innerText = "Yorumu Gönder";
            }
        }
    });
}

// ---------------------------------------------------------
// C) YORUMU EKRANA BASMA (SİLME BUTONU YOK)
// ---------------------------------------------------------
function renderComment(docId, data) {
    const newComment = document.createElement('div');
    newComment.classList.add('comment-item');
    
    // HTML İçeriği (Sadece İsim, Tarih, Yorum ve Like/Dislike)
    newComment.innerHTML = `
        <div class="comment-header">
            <span class="comment-author">${escapeHtml(data.name)}</span>
            <span class="comment-date">${data.date}</span>
        </div>
        <p style="color: #ddd;">${escapeHtml(data.text)}</p>
        <div class="comment-actions">
            <button class="action-btn like-btn">👍 <span class="count">${data.likes || 0}</span></button>
            <button class="action-btn dislike-btn">👎 <span class="count">${data.dislikes || 0}</span></button>
        </div>
    `;

    // LIKE İşlemi
    newComment.querySelector('.like-btn').addEventListener('click', async () => {
        const commentRef = doc(db, "comments", docId);
        await updateDoc(commentRef, { likes: increment(1) });
    });

    // DISLIKE İşlemi
    newComment.querySelector('.dislike-btn').addEventListener('click', async () => {
        const commentRef = doc(db, "comments", docId);
        await updateDoc(commentRef, { dislikes: increment(1) });
    });

    commentList.appendChild(newComment);
}

// Güvenlik (XSS)
function escapeHtml(text) {
    if (!text) return text;
    return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
}

// Smooth Scroll
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({ behavior: 'smooth' });
        }
    });
});