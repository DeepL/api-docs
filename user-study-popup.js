(() => {
  const USER_STUDY_KEY = 'deepl_user_study_popup_state';
  const USER_STUDY_DISMISSED = 'dismissed';
  const USER_STUDY_CLICKED = 'clicked';
  const CONSENT_KEY = 'deepl_cookie_consent';
  const CONSENT_ACCEPTED = 'accepted';
  const CONSENT_REJECTED = 'rejected';
  const SIGNUP_URL = 'https://greatquestion.co/deepl/GrnjONNw/apply';
  const SHOW_PROBABILITY = 0.1;
  const INITIAL_DELAY_MS = 2000;
  const RETRY_DELAY_MS = 1000;

  function buildSignupUrl(accountId) {
    const signupUrl = new URL(SIGNUP_URL);

    if (accountId) {
      signupUrl.searchParams.set('acc_id', accountId);
    }

    return signupUrl.toString();
  }

  async function getSignupUrl() {
    try {
      const accountId = await window.DeepLUser?.getAccountId?.();
      return buildSignupUrl(accountId);
    } catch (error) {
      console.error('Error building customer research signup URL:', error);
      return buildSignupUrl();
    }
  }

  function hasResolvedCookieBanner() {
    const consent = localStorage.getItem(CONSENT_KEY);
    return consent === CONSENT_ACCEPTED || consent === CONSENT_REJECTED;
  }

  function shouldSkipPopup() {
    const studyStatus = localStorage.getItem(USER_STUDY_KEY);
    return studyStatus === USER_STUDY_DISMISSED || studyStatus === USER_STUDY_CLICKED;
  }

  function markPopupState(state) {
    localStorage.setItem(USER_STUDY_KEY, state);
  }

  function removePopup(popup) {
    const card = popup.querySelector('#user-study-card');
    if (card) {
      card.classList.remove('slide-in');
      card.classList.add('slide-out');
    }

    window.setTimeout(() => {
      popup.remove();
    }, 300);
  }

  function renderPopup() {
    if (document.getElementById('user-study-popup')) return;

    const signupUrlPromise = getSignupUrl();

    const popup = document.createElement('div');
    popup.id = 'user-study-popup';
    popup.innerHTML = `
      <aside id="user-study-card" aria-label="User study invitation">
        <button id="user-study-close" type="button" aria-label="Dismiss user study invitation">&times;</button>
        <div id="user-study-content">
          <p id="user-study-eyebrow">Get paid to shape DeepL</p>
          <h3>Join our customer research panel</h3>
          <p>
            Share your info to be considered for paid customer interviews and research studies about the DeepL API.
          </p>
          <a id="user-study-cta" href="${SIGNUP_URL}" target="_blank" rel="noreferrer">Sign up</a>
        </div>
      </aside>
    `;

    document.body.appendChild(popup);

    signupUrlPromise.then((signupUrl) => {
      popup.querySelector('#user-study-cta')?.setAttribute('href', signupUrl);
    });

    window.setTimeout(() => {
      popup.querySelector('#user-study-card')?.classList.add('slide-in');
    }, 50);

    popup.querySelector('#user-study-close')?.addEventListener('click', () => {
      markPopupState(USER_STUDY_DISMISSED);
      removePopup(popup);
    });

    popup.querySelector('#user-study-cta')?.addEventListener('click', async (event) => {
      event.preventDefault();

      markPopupState(USER_STUDY_CLICKED);
      removePopup(popup);

      const signupUrl = await signupUrlPromise;
      window.open(signupUrl, '_blank', 'noopener,noreferrer');
    });
  }

  function maybeShowUserStudyPopup() {
    if (shouldSkipPopup()) return;

    if (!hasResolvedCookieBanner()) {
      window.setTimeout(maybeShowUserStudyPopup, RETRY_DELAY_MS);
      return;
    }

    if (Math.random() >= SHOW_PROBABILITY) return;

    renderPopup();
  }

  function initUserStudyPopup() {
    window.setTimeout(maybeShowUserStudyPopup, INITIAL_DELAY_MS);
  }

  window.getUserStudySignupUrlNow = getSignupUrl;
  window.showUserStudyPopupNow = function showUserStudyPopupNow() {
    localStorage.removeItem(USER_STUDY_KEY);

    if (!hasResolvedCookieBanner()) {
      localStorage.setItem(CONSENT_KEY, CONSENT_ACCEPTED);
    }

    renderPopup();
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initUserStudyPopup);
  } else {
    initUserStudyPopup();
  }
})();
