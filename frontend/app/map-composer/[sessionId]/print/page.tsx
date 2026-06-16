import { ComposerPrintClient } from "@/components/composer-print-client";

export default async function ComposerPrintPage({ params }: { params: Promise<{ sessionId: string }> }) {
  const { sessionId } = await params;
  return <ComposerPrintClient sessionId={sessionId} />;
}
