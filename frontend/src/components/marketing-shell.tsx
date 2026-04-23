import { ChevronRight, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";

interface MarketingShellProps {
  onOpenChat: () => void;
}

const navItems = ["Features", "Pricing", "Blog", "Changelog"];
const partnerMarks = ["ProLine", "hues", "Greenish", "Cloud", "Volume", "PinPoint"];

export function MarketingShell({ onOpenChat }: MarketingShellProps) {
  return (
    <main className="relative min-h-screen overflow-hidden bg-[color:var(--background)] text-[color:var(--foreground)]">
      <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.08)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.08)_1px,transparent_1px)] bg-[size:clamp(72px,10vw,124px)_clamp(72px,10vw,124px)] opacity-[0.16]" />
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_32%,rgba(119,84,255,0.22),transparent_22%),radial-gradient(circle_at_50%_55%,rgba(10,12,20,0.2),transparent_44%),linear-gradient(180deg,rgba(8,9,14,0.98)_0%,rgba(6,7,12,1)_100%)]" />
      <div className="absolute inset-x-0 top-0 h-24 border-b border-white/8" />
      <div className="absolute inset-x-0 top-[8.8rem] h-px bg-white/8" />
      <div className="absolute inset-x-0 bottom-[20.5rem] h-px bg-white/8" />
      <div className="absolute left-[6%] top-0 bottom-0 w-px bg-white/8 max-lg:hidden" />
      <div className="absolute right-[6%] top-0 bottom-0 w-px bg-white/8 max-lg:hidden" />

      <div className="relative mx-auto flex min-h-screen max-w-[1500px] flex-col px-6 sm:px-8 lg:px-12">
        <header className="flex h-24 items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex size-11 items-center justify-center rounded-2xl bg-white text-sm font-semibold text-black">
              VA
            </div>
            <span className="text-2xl font-semibold tracking-[-0.04em] text-white">Velora</span>
          </div>

          <nav className="hidden items-center gap-8 text-sm text-white/80 md:flex">
            {navItems.map((item) => (
              <button
                key={item}
                type="button"
                className="transition-colors hover:text-white"
                onClick={() => undefined}
              >
                {item}
              </button>
            ))}
          </nav>

          <div className="flex items-center gap-3">
            <Button variant="secondary" size="sm">
              Log in
            </Button>
            <Button size="sm" onClick={onOpenChat}>
              Get Started Today
            </Button>
          </div>
        </header>

        <section className="flex flex-1 flex-col items-center justify-center pb-24 pt-16 text-center sm:pt-20 lg:pt-24">
          <div className="inline-flex items-center gap-3 border border-white/10 bg-black/20 px-5 py-3 text-sm text-white/54 backdrop-blur-md">
            <div className="flex -space-x-2">
              <span className="flex size-7 items-center justify-center rounded-full border border-black/30 bg-[#c3e8ff] text-[0.62rem] font-semibold text-black">
                L
              </span>
              <span className="flex size-7 items-center justify-center rounded-full border border-black/30 bg-[#f0d1a2] text-[0.62rem] font-semibold text-black">
                M
              </span>
              <span className="flex size-7 items-center justify-center rounded-full border border-black/30 bg-[#d8c3ff] text-[0.62rem] font-semibold text-black">
                A
              </span>
            </div>
            <span>1,254 happy customers</span>
          </div>

          <div className="relative mt-14 w-full max-w-5xl">
            <div className="absolute inset-x-[20%] top-12 -z-10 h-52 rounded-full bg-[radial-gradient(circle,rgba(125,76,255,0.30),transparent_68%)] blur-3xl" />
            <h1 className="text-balance text-5xl leading-[0.94] font-medium tracking-[-0.065em] text-white sm:text-6xl lg:text-[6.4rem]">
              Support, der leise wirkt und trotzdem sofort hilft.
            </h1>
            <p className="mx-auto mt-7 max-w-2xl text-balance text-base leading-8 text-white/42 sm:text-lg">
              Ein reduziertes Premium-Frontend fuer ein simuliertes E-Commerce-Unternehmen.
              Der Fokus liegt auf dem kompakten KI-Concierge unten rechts, nicht auf einer
              ueberladenen Produktseite.
            </p>

            <div className="mx-auto mt-12 grid max-w-[26rem] grid-cols-1 border border-white/8 bg-black/18 shadow-[0_24px_90px_rgba(0,0,0,0.36)] backdrop-blur-md sm:grid-cols-2">
              <button
                type="button"
                className="border-b border-white/8 px-7 py-5 text-base text-white/88 transition-colors hover:bg-white/5 sm:border-r sm:border-b-0"
                onClick={() => undefined}
              >
                Request Demo
              </button>
              <button
                type="button"
                className="flex items-center justify-center gap-2 bg-[linear-gradient(90deg,#7a37f5,#b462ff)] px-7 py-5 text-base font-medium text-white transition-transform hover:scale-[1.01]"
                onClick={onOpenChat}
              >
                Frag KI
                <ChevronRight className="size-4" />
              </button>
            </div>

            <div className="mt-24 text-sm text-white/24">Join 4,000+ brands already growing</div>
            <div className="mt-10 grid grid-cols-2 gap-x-8 gap-y-6 text-3xl font-semibold tracking-[-0.05em] text-white/50 sm:grid-cols-3 lg:grid-cols-6">
              {partnerMarks.map((mark) => (
                <div key={mark}>{mark}</div>
              ))}
            </div>
          </div>

          <div className="mt-16 flex flex-wrap items-center justify-center gap-3 text-xs uppercase tracking-[0.24em] text-white/34">
            <div className="inline-flex items-center gap-2 rounded-full border border-white/8 bg-white/4 px-4 py-2">
              <Sparkles className="size-3.5 text-white/50" />
              FAQ Support heute
            </div>
            <div className="rounded-full border border-white/8 bg-white/4 px-4 py-2">
              Produkt-Tooling spaeter
            </div>
            <div className="rounded-full border border-white/8 bg-white/4 px-4 py-2">
              Video-taugliche UI
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
