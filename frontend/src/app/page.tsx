/*
 * Página temporal del esqueleto. La página pública definitiva corresponde a la
 * historia HU-03 (Sprint 2).
 */
export default function HomePage() {
  return (
    <>
      <header className="border-b border-hairline">
        <nav
          aria-label="Principal"
          className="mx-auto flex h-16 w-full max-w-content items-center justify-between px-4 md:px-8"
        >
          <p className="text-title font-semibold text-ink">CheckUrRef</p>
        </nav>
      </header>

      <main className="flex flex-1 flex-col">
        <section
          aria-labelledby="titulo-principal"
          className="mx-auto flex w-full max-w-content flex-col gap-4 px-4 py-12 md:px-8 md:py-20"
        >
          <p className="text-label font-semibold tracking-label text-muted uppercase">
            Esqueleto del proyecto
          </p>
          <h1 id="titulo-principal" className="text-display-md md:text-display-lg">
            Auditoría de referencias bibliográficas
          </h1>
          <p className="max-w-2xl">
            El frontend está listo para empezar a construir las historias de usuario del Sprint 1.
          </p>
        </section>
      </main>

      <footer className="border-t border-hairline">
        <p className="mx-auto w-full max-w-content px-4 py-6 text-small md:px-8">
          Universidad Estatal de Milagro · Ingeniería de Software
        </p>
      </footer>
    </>
  );
}
