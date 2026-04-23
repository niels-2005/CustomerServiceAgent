import { Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";

interface MarketingShellProps {
  onOpenChat: () => void;
}

const previewItems = [
  "24/7 Concierge fuer Versand, Retouren und Kontoanfragen",
  "Antwortet auf FAQs sofort und im Stil einer Premium Brand",
  "Erweiterbar fuer Produktberatung und Tool-Aufrufe in der naechsten Phase",
];

export function MarketingShell({ onOpenChat }: MarketingShellProps) {
  return (
    <main className="relative min-h-screen overflow-hidden bg-[color:var(--background)] text-[color:var(--foreground)]">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(92,122,255,0.22),_transparent_34%),radial-gradient(circle_at_70%_25%,_rgba(123,245,214,0.18),_transparent_28%),linear-gradient(180deg,_rgba(13,16,24,1)_0%,_rgba(8,10,16,1)_100%)]" />
      <div className="absolute inset-x-0 top-[-12rem] h-[28rem] bg-[radial-gradient(circle,_rgba(255,255,255,0.12)_0%,_transparent_62%)] blur-3xl" />
      <div className="absolute inset-x-0 bottom-[-18rem] h-[32rem] bg-[radial-gradient(circle,_rgba(81,127,255,0.18)_0%,_transparent_60%)] blur-3xl" />

      <div className="relative mx-auto flex min-h-screen max-w-7xl flex-col px-6 py-8 sm:px-8 lg:px-12">
        <header className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex size-11 items-center justify-center rounded-full border border-white/10 bg-white/8 text-sm uppercase tracking-[0.32em] text-white/80">
              VA
            </div>
            <div>
              <p className="text-xs uppercase tracking-[0.34em] text-white/45">Velora Atelier</p>
              <p className="text-sm text-white/72">Luxury essentials, delivered quietly.</p>
            </div>
          </div>

          <Button variant="secondary" size="sm" onClick={onOpenChat}>
            <Sparkles className="size-4" />
            Frag KI
          </Button>
        </header>

        <section className="flex flex-1 items-center py-16 sm:py-20">
          <div className="grid w-full gap-12 lg:grid-cols-[1.1fr_0.9fr] lg:items-end">
            <div className="max-w-3xl">
              <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/6 px-4 py-2 text-xs uppercase tracking-[0.28em] text-white/56">
                <span className="size-2 rounded-full bg-[color:var(--accent)] shadow-[0_0_18px_var(--accent)]" />
                Simuliertes E-Commerce Showcase
              </div>

              <h1 className="mt-8 max-w-4xl text-5xl leading-[0.95] font-semibold tracking-[-0.04em] text-white sm:text-6xl lg:text-8xl">
                Support, der sich wie Teil der Marke anfuhlt.
              </h1>
              <p className="mt-6 max-w-2xl text-base leading-7 text-white/68 sm:text-lg">
                Eine dunkle, video-taugliche Commerce-Oberflache mit eingebettetem KI-Support.
                Die Seite bleibt bewusst schlank. Der Fokus liegt auf dem sanften Einstieg in das
                Chat-Erlebnis unten rechts.
              </p>

              <div className="mt-10 flex flex-wrap items-center gap-4">
                <Button size="lg" onClick={onOpenChat}>
                  Frag KI
                </Button>
                <div className="text-sm text-white/44">
                  FAQ-Antworten heute. Produkt-Tooling als nachste Ausbaustufe.
                </div>
              </div>
            </div>

            <div className="relative">
              <div className="absolute inset-0 -z-10 rounded-[2rem] bg-[linear-gradient(140deg,_rgba(255,255,255,0.16),_rgba(255,255,255,0.02))] blur-3xl" />
              <div className="rounded-[2rem] border border-white/10 bg-white/[0.055] p-6 shadow-[0_36px_120px_rgba(0,0,0,0.48)] backdrop-blur-xl sm:p-8">
                <div className="flex items-center justify-between text-xs uppercase tracking-[0.24em] text-white/44">
                  <span>Customer Experience Layer</span>
                  <span>2026 Preview</span>
                </div>

                <div className="mt-8 space-y-4">
                  {previewItems.map((item) => (
                    <div
                      key={item}
                      className="rounded-3xl border border-white/8 bg-black/18 px-5 py-4 text-sm leading-6 text-white/76"
                    >
                      {item}
                    </div>
                  ))}
                </div>

                <div className="mt-8 rounded-[1.6rem] border border-[color:var(--accent)]/25 bg-[linear-gradient(180deg,rgba(89,130,255,0.14),rgba(255,255,255,0.03))] p-5">
                  <p className="text-xs uppercase tracking-[0.24em] text-[color:var(--accent-foreground)]/72">
                    Live entry point
                  </p>
                  <p className="mt-3 text-lg font-medium text-white">
                    Der eigentliche Fokus ist der Chat-Launcher. Alles andere rahmt ihn nur.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
