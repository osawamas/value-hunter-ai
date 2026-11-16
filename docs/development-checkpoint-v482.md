# VALUE HUNTER AI v482

The SGX close importer now checks the agreement's licensor, licensee,
product and HTTPS evidence URL before contacting the endpoint. This is
shared with the public and browser feed validator. The existing date
and usage-scope checks still apply. The HTTPS regression confirms that
incomplete agreement metadata causes zero requests to the provider.
Live licensed access and independent financial verification remain open.
