import Chat from "@/components/Chat";

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-black p-4 md:p-24 selection:bg-indigo-500/30">
      <div className="absolute inset-0 bg-[url('/grid.svg')] bg-center [mask-image:linear-gradient(180deg,white,rgba(255,255,255,0))]" />
      <div className="z-10 w-full max-w-5xl items-center justify-center font-mono text-sm lg:flex">
        <Chat />
      </div>
    </main>
  );
}
