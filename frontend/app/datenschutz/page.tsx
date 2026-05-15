import Link from "next/link";

export const metadata = {
  title: "Datenschutz – Bewerbungsavatar",
};

export default function DatenschutzPage() {
  return (
    <div className="max-w-2xl mx-auto px-6 py-12 text-sm text-zinc-700 dark:text-zinc-300 space-y-6">
      <h1 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-100">Datenschutzhinweise</h1>

      <section className="space-y-2">
        <h2 className="text-base font-semibold text-zinc-800 dark:text-zinc-200">Verantwortlicher</h2>
        <p>
          Matthias Kempka<br />
          E-Mail: <a href="mailto:commerce@mkempka.de" className="underline hover:text-zinc-900 dark:hover:text-white">commerce@mkempka.de</a>
        </p>
      </section>

      <section className="space-y-2">
        <h2 className="text-base font-semibold text-zinc-800 dark:text-zinc-200">Zweck dieser Anwendung</h2>
        <p>
          Dieser Bewerbungsavatar beantwortet Fragen zu meiner Person und Bewerbung auf Basis meiner Bewerbungsunterlagen.
          Er richtet sich ausschließlich an potenzielle Arbeitgeber und Recruitingverantwortliche.
        </p>
      </section>

      <section className="space-y-2">
        <h2 className="text-base font-semibold text-zinc-800 dark:text-zinc-200">Cookies</h2>
        <p>
          Diese Anwendung verwendet <strong>keine Cookies</strong>. Zur Identifikation Ihrer Sitzung wird
          stattdessen <code className="bg-zinc-100 dark:bg-zinc-800 px-1 rounded">sessionStorage</code> im
          Browser genutzt. Dort wird eine zufällig generierte Sitzungs-ID gespeichert, die beim Schließen
          des Browser-Tabs automatisch gelöscht wird.
        </p>
      </section>

      <section className="space-y-2">
        <h2 className="text-base font-semibold text-zinc-800 dark:text-zinc-200">Verarbeitete Daten</h2>
        <ul className="list-disc list-inside space-y-1">
          <li>
            <strong>Gesprächsinhalte:</strong> Ihre Fragen und die Antworten des Avatars werden in einer Datenbank
            gespeichert, um den Gesprächsverlauf innerhalb einer Sitzung zu erhalten.
          </li>
          <li>
            <strong>Sitzungs-ID:</strong> Eine anonyme, zufällig generierte UUID dient der Zuordnung Ihrer Anfragen
            zur laufenden Sitzung.
          </li>
          <li>
            <strong>Server- und Telemetrielogs:</strong> Die Anwendung erfasst technische Telemetriedaten für
            Betrieb und Fehleranalyse. Diese Logs können Ihre Eingaben (Gesprächsinhalt) enthalten.
          </li>
        </ul>
      </section>

      <section className="space-y-2">
        <h2 className="text-base font-semibold text-zinc-800 dark:text-zinc-200">Drittanbieter – KI-Verarbeitung</h2>
        <p>
          Ihre Nachrichten werden zur Verarbeitung an <strong>OpenRouter</strong> (openrouter.ai) übermittelt,
          einen Dienst, der den Zugang zu verschiedenen KI-Sprachmodellen vermittelt. Die Verarbeitung erfolgt
          auf Servern außerhalb dieser Anwendung, unter der Anweisung, nur Anbieter mit Zero Data Retention (ZDR) zu verwenden.
          Es gelten die Datenschutzbedingungen von OpenRouter.
        </p>
      </section>

      <section className="space-y-2">
        <h2 className="text-base font-semibold text-zinc-800 dark:text-zinc-200">Speicherdauer</h2>
        <p>
          Gesprächsdaten werden für den Betrieb der Anwendung vorgehalten. Es besteht kein Anspruch auf
          dauerhafte Verfügbarkeit. Bei Fragen zur Löschung wenden Sie sich bitte direkt an mich.
        </p>
      </section>

      <section className="space-y-2">
        <h2 className="text-base font-semibold text-zinc-800 dark:text-zinc-200">Ihre Rechte</h2>
        <p>
          Sie haben das Recht auf Auskunft, Berichtigung, Löschung und Einschränkung der Verarbeitung Ihrer
          Daten sowie auf Datenübertragbarkeit. Bitte wenden Sie sich dazu per E-Mail an den oben genannten
          Verantwortlichen.
        </p>
      </section>

      <div className="pt-4 border-t border-zinc-200 dark:border-zinc-800">
        <Link href="/" className="text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-100 underline">
          ← Zur Startseite
        </Link>
      </div>
    </div>
  );
}
