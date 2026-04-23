(function () {
  const backToTop = document.querySelector('[data-action="scroll-top"]');
  if (backToTop) {
    backToTop.addEventListener('click', function (event) {
      event.preventDefault();
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  }
})();
