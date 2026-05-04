/* Expose DeepL client state so docs scripts can personalize account links. */
window.DeepLUser = (() => {
  const API_BASE_URL = 'https://w.deepl.com/web';
  const API_PARAMS = 'request_type=jsonrpc&il=en&method=getClientState';
  const apiUrl = `${API_BASE_URL}?${API_PARAMS}`;

  const CTA_SELECTOR = '#topbar-cta-button a';
  const CTA_LABEL_SELECTOR = 'span.z-10';

  let clientStatePromise;

  function getClientState() {
    if (!clientStatePromise) {
      clientStatePromise = (async () => {
        try {
          const response = await fetch(
            apiUrl,
            {
              method: "POST",
              headers: {
                "Accept": "application/json",
                "Content-Type": "application/json"
              },
              body: JSON.stringify({
                jsonrpc: "2.0",
                method: "getClientState"
              }),
              credentials: 'include'
            }
          );
          const json = await response.json();

          return json?.result;

        } catch (error) {
          console.error('Error fetching user data:', error);
          clientStatePromise = null;
        }
      })();
    }
    return clientStatePromise;
  }

  function getApiSubscription(clientState) {
    return clientState?.featureSet?.subscription?.api;
  }

  async function getAccountId() {
    const clientState = await getClientState();
    return clientState?.loginState?.accountId;
  }

  function findCtaButton() {
    const link = document.querySelector(CTA_SELECTOR);
    if (!link) return null;

    return {
      link,
      label: link.querySelector(CTA_LABEL_SELECTOR),
    };
  }

  function setCtaButton(label, href) {
    const cta = findCtaButton();
    if (!cta) return false;

    if (cta.label && cta.label.textContent !== label) {
      cta.label.textContent = label;
    }

    if (cta.link.href !== href) {
      cta.link.href = href;
    }

    return true;
  }

  function resolveCtaState(clientState) {
    if (!clientState?.loginState) return null;

    if (getApiSubscription(clientState)) {
      return { label: 'Dashboard', href: 'https://www.deepl.com/en/your-account/keys' };
    }

    // TODO: Update link once self-serve multisub lets users add an API
    // subscription to their existing translate account.
    // Then we can display separate links for anon vs non-API users.
    return { label: 'Free API Key', href: 'https://www.deepl.com/en/checkout?is_api=true' };
  }

  async function initNavbarCta() {
    const clientState = await getClientState();
    const cta = resolveCtaState(clientState);
    if (!cta) return;

    // Mintlify is an SPA: the nav may not be rendered yet.
    let attempts = 0;
    const poll = setInterval(() => {
      if (setCtaButton(cta.label, cta.href) || ++attempts >= 20) {
        clearInterval(poll);
      }
    }, 500);

    // Re-apply when Mintlify re-renders the nav during SPA navigation.
    let rafPending = false;
    new MutationObserver(() => {
      if (rafPending) return;
      rafPending = true;
      requestAnimationFrame(() => {
        setCtaButton(cta.label, cta.href);
        rafPending = false;
      });
    }).observe(document.body, { childList: true, subtree: true });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initNavbarCta);
  } else {
    initNavbarCta();
  }

  return { getClientState, getAccountId };
})();

window.getDeepLClientStateNow = function getDeepLClientStateNow() {
  return window.DeepLUser?.getClientState?.();
};
