/** Descarga un texto generado en el navegador como un archivo. */
export function downloadTextFile(fileName: string, content: string, mimeType: string): void {
  const url = URL.createObjectURL(new Blob([content], { type: mimeType }));
  const link = document.createElement("a");
  link.href = url;
  link.download = fileName;
  document.body.append(link);
  link.click();
  link.remove();
  // Algunos navegadores leen el archivo después del clic: no se libera en el mismo instante.
  setTimeout(() => URL.revokeObjectURL(url), 0);
}
