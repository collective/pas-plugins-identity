/**
 * Handing text to the browser as a file.
 * @module helpers/download
 */

/**
 * Save text as a file, through the browser's own download.
 *
 * Built in the page rather than linked to: the text came back from an API
 * call that carried the user's credentials in a header, and a plain link to
 * that endpoint would be requested without them.
 *
 * @param filename The name the browser offers to save it under.
 * @param text The file's content.
 * @param type Its media type.
 */
export function downloadText(
  filename: string,
  text: string,
  type = 'application/xml',
): void {
  const url = URL.createObjectURL(new Blob([text], { type }));
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  // Attached for the click: some browsers ignore one on a detached anchor.
  document.body.appendChild(link);
  link.click();
  link.remove();
  // Released once the click has been handled, not before it.
  setTimeout(() => URL.revokeObjectURL(url), 0);
}
