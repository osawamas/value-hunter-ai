package jp.valuehunter.privatewatch;

import org.junit.Test;
import static org.junit.Assert.*;

public class SecAccessTest {
    @Test public void onlyOfficialSecHostsReceiveIdentity() {
        assertTrue(SecAccess.isSecHost("www.sec.gov"));
        assertTrue(SecAccess.isSecHost("data.sec.gov"));
        assertFalse(SecAccess.isSecHost("www.sec.gov.example.org"));
        assertFalse(SecAccess.isSecHost("api.nasdaq.com"));
    }

    @Test public void missingOrMalformedContactCannotProduceFakeIdentity() {
        assertFalse(SecAccess.validEmail(""));
        assertFalse(SecAccess.validEmail("example@example.com\\r\\nInjected: yes"));
        assertFalse(SecAccess.validEmail("not-an-email"));
        try {
            SecAccess.userAgent("");
            fail("Missing email must not send SEC requests");
        } catch (SecAccess.MissingContactException expected) {
            // SEC access remains blocked until user supplies a real address.
        }
    }

    @Test public void declaredIdentityContainsContact() throws Exception {
        assertEquals("ValueHunterAI PersonalResearch user@example.org",
                SecAccess.userAgent("user@example.org"));
    }
}
