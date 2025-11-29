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

// --- YEREL HAFIZA YÖNETİMİ (LOCAL STORAGE) ---
const getLocalVotes = () => JSON.parse(localStorage.getItem('ghosty_user_votes') || '{}');

const saveLocalVote = (docId, type) => {
    const votes = getLocalVotes();
    votes[docId] = type;
    localStorage.setItem('ghosty_user_votes', JSON.stringify(votes));
};

const removeLocalVote = (docId) => {
    const votes = getLocalVotes();
    delete votes[docId];
    localStorage.setItem('ghosty_user_votes', JSON.stringify(votes));
};

// ---------------------------------------------------------
// A) VERİLERİ CANLI ÇEKME
// ---------------------------------------------------------
const q = query(collection(db, "comments"), orderBy("timestamp", "desc"));

onSnapshot(q, (snapshot) => {
    commentList.innerHTML = ""; 

    if (snapshot.empty) {
        if(noCommentsMsg) {
            noCommentsMsg.style.display = 'block';
            commentList.appendChild(noCommentsMsg);
        }
    } else {
        if(noCommentsMsg) noCommentsMsg.style.display = 'none';
        
        const userVotes = getLocalVotes();

        snapshot.forEach((document) => {
            const data = document.data();
            const docId = document.id;
            renderComment(docId, data, userVotes[docId]);
        });
    }
});

// ---------------------------------------------------------
// B) OY VERME MANTIĞI (Geri Alma ve Değiştirme Dahil)
// ---------------------------------------------------------
const handleVote = async (docId, voteType) => {
    const userVotes = getLocalVotes();
    const currentVote = userVotes[docId]; // Kullanıcının şu anki oyu ('like', 'dislike' veya undefined)
    const commentRef = doc(db, "comments", docId);

    // SENARYO 1: AYNI BUTONA TEKRAR TIKLADI (GERİ ALMA)
    if (currentVote === voteType) {
        // Oyu veritabanından sil (Sayıyı 1 azalt)
        await updateDoc(commentRef, {
            [voteType + 's']: increment(-1) // örn: likes - 1
        });
        // Hafızadan sil
        removeLocalVote(docId);
    } 
    // SENARYO 2: FARKLI BUTONA TIKLADI (DEĞİŞTİRME)
    else if (currentVote) {
        // Eski oyu azalt, yeni oyu artır
        await updateDoc(commentRef, {
            [currentVote + 's']: increment(-1), // Eski oyu düş
            [voteType + 's']: increment(1)      // Yeni oyu artır
        });
        // Hafızayı güncelle
        saveLocalVote(docId, voteType);
    } 
    // SENARYO 3: İLK DEFA OY VERİYOR
    else {
        await updateDoc(commentRef, {
            [voteType + 's']: increment(1)
        });
        saveLocalVote(docId, voteType);
    }
};

// ---------------------------------------------------------
// C) YENİ YORUM EKLEME
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
// D) RENDER FONKSİYONU
// ---------------------------------------------------------
function renderComment(docId, data, userVoteStatus) {
    const newComment = document.createElement('div');
    newComment.classList.add('comment-item');
    
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

    const likeBtn = newComment.querySelector('.like-btn');
    const dislikeBtn = newComment.querySelector('.dislike-btn');

    // Görsel Durumu Ayarla
    if (userVoteStatus === 'like') {
        likeBtn.classList.add('voted');
    } else if (userVoteStatus === 'dislike') {
        dislikeBtn.classList.add('voted');
    }

    // Tıklama Olayları (Tek bir handleVote fonksiyonuna yönlendiriyoruz)
    likeBtn.addEventListener('click', () => handleVote(docId, 'like'));
    dislikeBtn.addEventListener('click', () => handleVote(docId, 'dislike'));

    commentList.appendChild(newComment);
}

function escapeHtml(text) {
    if (!text) return text;
    return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
}

document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) target.scrollIntoView({ behavior: 'smooth' });
    });
});