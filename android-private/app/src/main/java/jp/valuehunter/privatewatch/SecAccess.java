package jp.valuehunter.privatewatch;

import android.content.Context;

import java.io.IOException;
import java.util.Locale;
import java.util.regex.Pattern;

/** Honest SEC traffic identity. Private contact stays on-device and is sent only to SEC hosts. */
final class SecAccess {
    static final String CONTACT_KEY = "sec_contact_email";
    private static final Pattern EMAIL = Pattern.compile(
            "[A-Za-z0-9._%+\\-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}");

    private SecAccess() {}

    static boolean isSecHost(String host) {
        return "www.sec.gov".equalsIgnoreCase(host) || "data.sec.gov".equalsIgnoreCase(host);
    }

    static boolean validEmail(String candidate) {
        return candidate != null && candidate.length() <= 254 && candidate.length() >= 6
                && EMAIL.matcher(candidate).matches()
                && candidate.indexOf('\n') < 0 && candidate.indexOf('\r') < 0;
    }

    static String contact(Context context) {
        return ScanWorker.prefs(context).getString(CONTACT_KEY, "").trim();
    }

    static String userAgent(String email) throws MissingContactException {
        if (!validEmail(email)) throw new MissingContactException();
        return "ValueHunterAI PersonalResearch " + email;
    }

    static String userAgent(Context context) throws MissingContactException {
        return userAgent(contact(context));
    }

    static final class MissingContactException extends IOException {
        MissingContactException() {
            super("SEC contact not configured");
        }
    }
}
