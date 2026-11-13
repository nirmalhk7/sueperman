"use client";
import { useParams } from "next/navigation";
import { RunResults } from "../../components";
export default function Page() {
  const { id } = useParams<{ id: string }>();
  return (
    <>
      <span className="eyebrow">Purchase investigation</span>
      <h1>Your evidence trail.</h1>
      <p>
        Every decision has a source. Review exact matches, excluded products,
        and missing information.
      </p>
      <RunResults id={id} />
    </>
  );
}
