import { fireEvent, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import SearchBar from "@/components/SearchBar";
import { renderWithProviders } from "../testUtils";

const options = [
   { id: "zoetermeer", label: "Zoetermeer" },
   { id: "zoeterwoude", label: "Zoeterwoude" },
   { id: "zwolle", label: "Zwolle" },
];

function renderSearchBar() {
   const onSelect = vi.fn();
   renderWithProviders(<SearchBar regionCategory="GEMEENTE" options={options} onSelect={onSelect} />);
   return { onSelect, input: screen.getByRole("combobox", { name: "Zoek gemeente" }) };
}

describe("SearchBar", () => {
   // jsdom has no layout, so no scrollIntoView; the component calls it for the highlighted option.
   beforeEach(() => {
      Element.prototype.scrollIntoView = vi.fn();
   });

   it("exposes the suggestions as a listbox and announces how many there are", () => {
      const { input } = renderSearchBar();
      expect(input).toHaveAttribute("aria-expanded", "false");

      fireEvent.change(input, { target: { value: "zoeter" } });

      expect(input).toHaveAttribute("aria-expanded", "true");
      expect(screen.getByRole("listbox", { name: "Zoek gemeente" })).toBeInTheDocument();
      expect(screen.getAllByRole("option")).toHaveLength(2);
      expect(screen.getByRole("status")).toHaveTextContent("2 resultaten");
   });

   it("announces when nothing matches", () => {
      const { input } = renderSearchBar();

      fireEvent.change(input, { target: { value: "xyz" } });

      expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
      expect(screen.getByRole("status")).toHaveTextContent("Geen resultaten");
   });

   it("marks the option chosen with the arrow keys as selected", () => {
      const { input, onSelect } = renderSearchBar();
      fireEvent.change(input, { target: { value: "zoeter" } });

      fireEvent.keyDown(input, { key: "ArrowDown" });
      fireEvent.keyDown(input, { key: "ArrowDown" });

      const selected = screen.getByRole("option", { name: "Zoeterwoude" });
      expect(selected).toHaveAttribute("aria-selected", "true");
      expect(input).toHaveAttribute("aria-activedescendant", selected.id);

      fireEvent.keyDown(input, { key: "Enter" });
      expect(onSelect).toHaveBeenCalledWith(options[1]);
   });
});
