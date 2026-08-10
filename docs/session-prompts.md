# Session prompts

The user prompts that produced this catalog, in order, reproduced verbatim.
Kept as a record of how the catalog was specified — the requirements arrived
incrementally, and several of the catalog's rules (native CRS, browse-vs-data
hosts, legends) trace directly to a correction below.

Notes in brackets are editorial; everything else is the prompt as written.
Screenshots that accompanied prompts are described in brackets where they
carried the substance.

---

1. *(via the `/portolan:portolan-bootstrap` skill)*

   > can you make a complete portolan catalog from the 8 datasets at
   > https://developer.trimet.org/gis/ - use the latest portolan spec from
   > ~/repos/portolan-spec and add 3-5 styles for each entity, based on
   > analysis of the data, plus great agents.md files as described in the spec
   > best practices. Do include links to each of the original shapefile / kml /
   > metadata, and then adapt to pmtiles / geoparquet and mine the metadata. Do
   > research anything else you can find about these datasets, to include more
   > context. And be sure to include trimet logos in the catalog.

2. > Oh, and structure this as a github repo we'll put up in
   > github.com/cholmes/portolan-catalog-trimet, modeled after
   > ~/repos/ftw-data-catalog and ~/repos/portolan-nl-catalog

3. *(checkpoint answers: license `other` with a link to TriMet's terms;
   publish to Source Cooperative at `cholmes/trimet`; host contact
   "Chris Holmes, cholmes@9eo.org")*

4. *(with a screenshot of maps.trimet.org)*

   > Oh, and do reuse the cartography from https://developer.trimet.org/gis/ -
   > see if you can find the source styles anywhere, or else you can just try
   > to match them.

5. *(second maps.trimet.org screenshot)*

   > is another

6. *(screenshot of trimet.org/home/routes/)*

   > Also can explore https://trimet.org/home/routes/

7. > also check out 'rtp' style to see if it can match any of the gis layers.

8. > in tiles.trimet.org

9. > Can you include the source SLD's in the catalog as well?

10. > what do we need for chitiler to work? I'd like to use that, at least in
    > the future.

    *(follow-up checkpoint answer: install node@24 via Homebrew)*

11. > can you do the installation in a subagent? ANd/or keep going on the main
    > thread in some way?

12. > Do them as webp -
    > https://github.com/portolan-sdi/portolan-spec/pull/121 will land soon.

13. > I don't think you need to reconstruct them? Just convert your png's
    > direct to webp?

14. > continue

15. > publish and push

16. > continue

17. *(screenshot of the newly registered source.coop/cholmes/trimet page)*

    > I think I just got it working. There is a broken image on the readme.

18. *(three screenshots: dead collection links, raw "Additional Resources"
    links, unlinked URLs in the STAC description)*

    > Decent start. A few things: * I see obvious links that I can't click on,
    > like 's a link back to trimet.org' - could you make those links?* links
    > on these go to data.source.coop - they should just go to source.coop so
    > that they render as readme's - right now they don't work -
    > https://data.source.coop/cholmes/trimet/rail-lines/ is wrong,
    > https://source.coop/cholmes/trimet/rail-lines/ is right. Put a link to
    > https://cholmes.github.io/trimet-data-browser for people to explore,
    > prominently. Add stac table metadata of the fields to all of them. Also
    > [thumbnails] go to data.source.coop - they should also go to source.coop
    > so they get rendered nicely. in the stac description there are links
    > that aren't actual links - can you make them markdown links so they can
    > be clicked on? Also you said 's, reprojected to WGS84 from TriMet's
    > NAD83(HARN) / Oregon North (ft)' - can you not reproject the geoparquets?
    > Keep them as the native, (and use pmtiles for the reprojected /
    > visualization)

19. > 'developer.trimet.org/gis' is also one that isn't a link. Can you also
    > mention the agent instructions in the markdown for the stac? So it's not
    > only a link.

20. > did you published?

21. *(two screenshots of the rendered STAC description and a collection README)*

    > this is off in a few ways - 'explore in the interactive map' is weird as
    > it's basically just a self link - can just remove that one. And ' Start
    > at the catalog agent guide.' seems extraneous - just link in the text
    > 'AGENTS.md agent guide' and in the readme, i'd not phrase it 'interactive
    > map', call it the 'data browser' or 'interactive data page' something
    > that's more than just an interactive map - it's where you can download
    > the data, preview the data, see the license, links out, etc.

22. > that last thing is fine.

    *(re: the thumbnail image linking to the data browser)*

23. > how big is this data? How much would it cost to host on aws?

24. *(screenshot of the "About this mirror" section)*

    > could this be more clear that the catalog is maintained on github, and
    > the browser at https://github.com/cholmes/portolan-catalog-trimet, and
    > that contributions / improvements to both are welcome - just file
    > issues / open pr's.

25. *(two screenshots: keyword tags on a collection page vs KML/Parquet/ZIP
    badges on the catalog cards)*

    > has nice tags but [the cards] just shows kml / parquet / zip for each of
    > them. Any idea why?

26. > ok, that's fine. Oh, also none of the styles have legends, while other
    > portolan catalogs do. Is it possible to get it so their styles have
    > legends?

27. > Can you write a blurb of guidance for future ai agents of what is needed
    > to structure the styles so that legends work?

28. *(screenshot of "Additional Resources" linking to raw markdown)*

    > https://data.source.coop/cholmes/trimet/README.md is the catalog readme
    > link. Can you have it be to https://source.coop/cholmes/trimet which
    > will render the readme and also have the files in it? And catch any
    > other data.source.coop links and change them to source.coop if they are
    > things that will render (readme and agents.md)

29. *(two screenshots of developer.trimet.org typography; about the data
    browser, interrupted before work began)*

    > Is it possible to match the fonts and link styles more exactly from
    > https://developer.trimet.org/ /
    > https://developer.trimet.org/gis/meta_tm_rail_stops.shtml - so it feels
    > like part of the developer site? Like links with underlines, same font
    > sizes, etc?

30. > can you make a file that has all the prompts I did for this session?

    *(this file)*
