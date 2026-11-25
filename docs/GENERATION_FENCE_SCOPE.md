# Router snapshot inspection fence — scope and release gate

This patch ports the same-runtime identity witness from draft #53 onto the
latest canonical `.atto` router mainline without resurrecting legacy router
source or replacing the exact-golden native guest suite.

## Invariants this patch enforces
- A new private `RouterGenerationWitness` is created on **every** build,
  including consecutive builds of an unchanged RouterBuilder.
- Each Decision retains the witness from its producing immutable Router.
- Captures and Allow inspection return empty when the borrowed Decision
  originated on another immutable Router, **even if both route tables,
  public metadata, handler IDs and route templates are identical**.
- The admission check occurs **before** trusting or indexing any Decision's
  public endpoint metadata. Existing path/target metadata validation remains.
- The decision inspector also requires that 405/automatic-OPTIONS carry no
  target index, handler, pipeline, contract, operation or suppressed-body flag.
  Identity check alone never authorizes contradictory Decision metadata.
- A separate 26-assertion decision-kind matrix tests local vs foreign
  match, 405, automatic-OPTIONS and newly rebuilt snapshots.
- The existing native guest fixture harness executes a 16-assertion
  `guest_generation_witness.atto` on real compiler, with exact golden stdout.

## Security boundary NOT provided
The witness is a **same-runtime metadata-inspection fence only**. It is not a
runtime-minted supervisor/tenant capability and does not authorize execution,
IPC, cross-actor mail, hot reload, response transfer or a request's epoch.
Public Decision fields remain *data*, never bearer authority.

Issue #52 stays open until owner-minted unforgeable capabilities, generation
revocation, actor/supervisor epoch validation, response-owner transfer,
in-flight drain/abort, cancellation and physical quiescence are enforced and
tested in the runtime/HTTP adapter. AttoLang LLVM, .NET and AOT conformance
need their own executed evidence. Do not merge this patch as completion of #52.

## CI acceptance
1. Match original PR head **full Git tree**, not just selected blobs.
2. Check/build pinned compiler source from `SOURCE_REF`.
3. Run baseline router guest + every existing `guest_*.atto` + witness fixture;
   compare stdout against exact committed goldens.
4. Prove a negative mutation deleting the `from_generation` gate causes
   wrong guest output, not merely a parser/compile error.
5. Keep host-only/zero-step admission failures separate from guest proof.
6. Obtain independent review and maintain the remaining runtime release gate.
