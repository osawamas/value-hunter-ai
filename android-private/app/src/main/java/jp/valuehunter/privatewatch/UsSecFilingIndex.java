package jp.valuehunter.privatewatch;

import org.json.JSONException;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.StringReader;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;
import java.time.format.ResolverStyle;
import java.util.HashSet;
import java.util.Locale;
import java.util.Set;
import java.util.regex.Pattern;

final class UsSecFilingIndex {
    private static final String RELEASE_LABEL = "Last Data Received:";
    private static final String HEADER = "CIK|Company Name|Form Type|Date Filed|File Name";
    private static final DateTimeFormatter RELEASE = DateTimeFormatter.ofPattern("MMM d, uuuu", Locale.US)
            .withResolverStyle(ResolverStyle.STRICT);
    private static final Pattern PATH = Pattern.compile("edgar/data/[0-9]+/[0-9]{10}-[0-9]{2}-[0-9]{6}\\.txt");

    static String address(LocalDate day) {
        return "https://www.sec.gov/Archives/edgar/daily-index/" + day.getYear()
                + "/QTR" + ((day.getMonthValue() - 1) / 3 + 1)
                + "/master." + day.format(DateTimeFormatter.BASIC_ISO_DATE) + ".idx";
    }

    static Set<Integer> issuers(String text, LocalDate expected) throws IOException, JSONException {
        var found = new HashSet<Integer>();
        boolean dateMatches = false;
        boolean headerFound = false;
        try (var source = new BufferedReader(new StringReader(text))) {
            for (String line; (line = source.readLine()) != null;) {
                if (line.startsWith(RELEASE_LABEL)) {
                    dateMatches = expected.equals(LocalDate.parse(line.substring(RELEASE_LABEL.length()).trim(), RELEASE));
                }
                if (HEADER.equals(line.trim())) {
                    headerFound = true;
                    break;
                }
            }
            String separator = source.readLine();
            if (!dateMatches || !headerFound || separator == null || !separator.trim().matches("-{5,}")) {
                throw new JSONException("Missing or misdated SEC daily index");
            }
            for (String line; (line = source.readLine()) != null;) {
                if (line.trim().isEmpty()) continue;
                var columns = line.split("\\|", -1);
                if (columns.length != 5 || columns[1].isEmpty() || columns[2].isEmpty()
                        || !PATH.matcher(columns[4]).matches()) {
                    throw new JSONException("Invalid SEC daily index row");
                }
                int cik = Integer.parseInt(columns[0]);
                String value = columns[3];
                LocalDate filed = value.length() == 8
                        ? LocalDate.parse(value, DateTimeFormatter.BASIC_ISO_DATE) : LocalDate.parse(value);
                // The index also includes corrections carrying earlier filing dates.
                if (cik <= 0 || filed.isAfter(expected)) throw new JSONException("Invalid SEC filing date or issuer");
                found.add(cik);
            }
        } catch (DateTimeParseException | NumberFormatException invalid) {
            throw new JSONException("Invalid SEC index date or issuer");
        }
        if (found.isEmpty()) throw new JSONException("Empty SEC daily index");
        return found;
    }

    private UsSecFilingIndex() {}
}
