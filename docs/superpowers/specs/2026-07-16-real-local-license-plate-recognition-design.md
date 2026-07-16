# Real local license-plate recognition design

**Date:** 2026-07-16

## Goal

Run `license-plate-recognition-system` without the mock provider and verify that an uploaded real image is processed by a real OCR engine. A valid outcome is either a plate number extracted from OCR output or an explicit “no plate recognized” error. The system must not fabricate a plate number or silently fall back to mock data.

## Scope

This change implements the existing `local` provider with the Tesseract installation already available on the machine. It does not add plate detection, train a model, change the frontend layout, or implement the `ai` provider.

## Architecture

`LocalPlateRecognizer` remains behind the existing `PlateRecognizer` interface and is selected by `RECOGNIZER_PROVIDER=local`. `LOCAL_MODEL_PATH` identifies the Tesseract executable rather than a learned model file.

The recognizer will invoke Tesseract directly with an argument list, not through a shell. It will request Chinese and English OCR, collect text and confidence data, normalize candidate text, and match Chinese conventional and new-energy plate formats. This keeps the provider isolated from the API, storage, and history layers.

No Python OCR wrapper is required. The installed Tesseract process is the real recognition engine.

## Data flow

1. The user uploads a JPG, PNG, or WEBP image through the existing page.
2. `RecognitionService` validates and saves the image.
3. `LocalPlateRecognizer` verifies that `LOCAL_MODEL_PATH` names an executable file.
4. The recognizer invokes Tesseract with `chi_sim+eng`, a bounded timeout, and TSV output so confidence values are available.
5. OCR tokens are normalized without substituting or inventing characters.
6. The recognizer searches the normalized OCR text for a supported Chinese plate pattern.
7. If a plate is found, it returns the exact normalized match, the mean confidence of usable OCR tokens, provider `local`, and elapsed time.
8. If no plate is found, it raises an `AppError` that states that no plate was recognized.
9. Existing service behavior records both success and failure in SQLite.

## Plate matching

The parser accepts standard mainland Chinese plates and new-energy formats. It recognizes a Chinese province abbreviation followed by a Latin letter and the appropriate alphanumeric suffix. Ambiguous OCR output that does not satisfy a plate pattern is rejected rather than repaired heuristically.

OCR confidence is derived only from non-negative Tesseract TSV token confidence values and normalized to the existing `0..1` API range. It is metadata, not a claim that the plate match is correct.

## Error handling

The provider returns distinct application errors for:

- missing `LOCAL_MODEL_PATH`;
- missing or non-file executable path;
- Tesseract timeout;
- Tesseract process failure;
- unreadable or malformed OCR output;
- successful OCR execution with no plate-format match.

Errors remain visible through the current Chinese API and frontend messages. There is no fallback to `mock` or `ai`.

## Configuration and launch

The application will run with:

```text
RECOGNIZER_PROVIDER=local
LOCAL_MODEL_PATH=C:\Program Files\Tesseract-OCR\tesseract.exe
```

It will be launched on `http://127.0.0.1:8088` using the existing virtual environment. The server should remain running after verification.

## Verification

Automated tests will cover configuration validation, successful parsing of representative Tesseract output, no-match behavior, process failure, and timeout without invoking mock data.

End-to-end verification will then:

1. request `/api/config` and confirm `provider` is `local`;
2. request `/` and confirm the real frontend is served;
3. submit the existing real image to `POST /api/recognitions`;
4. observe that Tesseract processed it and that the API returns either a real matched plate or the explicit no-match error;
5. inspect recent history to confirm the `local` provider recorded the attempt;
6. interact with the browser page and confirm the same user-visible result.

The agreed acceptance level is real processing rather than guaranteed recognition accuracy on the existing image.
